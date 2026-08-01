from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import platform
import shutil
import sqlite3
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


STABLE_VERSION = "1.0.0"
STABLE_RELEASE_ID = "MMRF-1.0.0"
RELEASE_MANIFEST_SCHEMA = "mmrf-stable-release-manifest-1.0"
STABLE_DATASET_SCHEMA = "mmrf-data-lake-manifest-1.0"

FROZEN_SAFETY_FIELDS = (
    "source_factor_relations",
    "rsa_target_endpoint",
    "factor_candidate_endpoint",
    "range_narrowing_endpoint",
    "exact_prime_list_endpoint",
    "raw_factor_export",
)

FROZEN_SEMANTICS = {
    "logical_cid": (
        "CID is the SHA-256 identity of canonical logical column content, "
        "not the transport container."
    ),
    "public_classification": (
        "Only L0_PUBLIC_MATH data can enter the public stable dataset."
    ),
    "query_surface": (
        "Public queries are aggregate-only and may not accept target "
        "integers, RSA moduli, factors, candidates or narrowing requests."
    ),
    "governance_precedence": (
        "Safety validation runs before review counting or promotion."
    ),
    "review_uniqueness": (
        "Promotion requires at least two distinct approved reviewer "
        "identities; duplicate reviewers do not increase quorum."
    ),
    "provenance": "Promoted datasets require a hash-bound acyclic provenance graph.",
    "citation": (
        "Stable citations bind the dataset manifest, promotion receipt "
        "and provenance graph."
    ),
    "controlled_default": (
        "Controlled Vault, Enclave and network components are disabled "
        "in the default public installation profile."
    ),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def generate_release_signing_keypair(
    private_path: Path,
    public_path: Path,
) -> dict:
    private = Ed25519PrivateKey.generate()
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    os.chmod(private_path, 0o600)
    public_path.write_bytes(
        private.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return {
        "private_key_path": str(private_path),
        "public_key_path": str(public_path),
        "public_key_sha256": file_sha256(public_path),
    }


def load_private(path: Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(
        Path(path).read_bytes(),
        password=None,
    )
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("not Ed25519 private key")
    return key


def load_public(path: Path) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(Path(path).read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise TypeError("not Ed25519 public key")
    return key


def sign_release_document(
    core: Mapping[str, Any],
    private_key_path: Path,
) -> dict:
    signature = load_private(private_key_path).sign(
        canonical_json(core).encode("utf-8")
    )
    signed = {**dict(core), "signature_ed25519": b64(signature)}
    return {
        **signed,
        "document_sha256": sha256_json(signed),
    }


def verify_signed_release_document(
    document: Mapping[str, Any],
    public_key_path: Path,
) -> dict:
    try:
        signed = {
            key: value
            for key, value in document.items()
            if key != "document_sha256"
        }
        core = {
            key: value
            for key, value in signed.items()
            if key != "signature_ed25519"
        }
        load_public(public_key_path).verify(
            unb64(document["signature_ed25519"]),
            canonical_json(core).encode("utf-8"),
        )
        checks = {
            "signature_ok": True,
            "document_hash_ok": (
                document.get("document_sha256")
                == sha256_json(signed)
            ),
        }
        return {
            "valid": all(checks.values()),
            "checks": checks,
            "reason": None if all(checks.values()) else "document_hash_mismatch",
        }
    except Exception as exc:
        return {
            "valid": False,
            "checks": {},
            "reason": f"signature_or_structure_invalid:{type(exc).__name__}",
        }


def validate_safety(safety: Mapping[str, Any]) -> dict:
    checks = {
        "classification_ok": (
            safety.get("classification") == "L0_PUBLIC_MATH"
        ),
    }
    for field in FROZEN_SAFETY_FIELDS:
        checks[f"{field}_false"] = safety.get(field) is False
    return {
        "valid": all(checks.values()),
        "checks": checks,
        "reason": None if all(checks.values()) else "stable_safety_violation",
    }


def validate_promotion_bindings(
    *,
    candidate_manifest: Mapping[str, Any],
    promotion_receipt: Mapping[str, Any],
    provenance_graph: Mapping[str, Any],
    citation: Mapping[str, Any],
) -> dict:
    safety = validate_safety(candidate_manifest.get("safety", {}))
    provenance_core = {
        key: value
        for key, value in provenance_graph.items()
        if key not in {"graph_sha256", "dag_valid"}
    }
    citation_core = {
        key: value
        for key, value in citation.items()
        if key != "citation_sha256"
    }
    checks = {
        "candidate_schema_ok": (
            candidate_manifest.get("schema")
            == "mmrf-data-lake-manifest-0.9"
        ),
        "promotion_candidate_binding": (
            promotion_receipt.get("candidate_manifest_sha256")
            == candidate_manifest.get("manifest_sha256")
        ),
        "promotion_quorum": (
            int(promotion_receipt.get("approval_count", 0))
            >= int(promotion_receipt.get("approval_threshold", 2))
            >= 2
        ),
        "distinct_reviewers": (
            len(set(promotion_receipt.get("reviewers", [])))
            == len(promotion_receipt.get("reviewers", []))
            >= 2
        ),
        "provenance_hash_ok": (
            provenance_graph.get("graph_sha256")
            == sha256_json(provenance_core)
        ),
        "provenance_dag_declared": (
            provenance_graph.get("dag_valid") is True
        ),
        "citation_hash_ok": (
            citation.get("citation_sha256")
            == sha256_json(citation_core)
        ),
        "citation_manifest_binding": (
            citation.get("manifest_sha256")
            == candidate_manifest.get("manifest_sha256")
        ),
        "citation_promotion_binding": (
            citation.get("promotion_receipt_sha256")
            == promotion_receipt.get("receipt_sha256")
        ),
        "citation_provenance_binding": (
            citation.get("provenance_graph_sha256")
            == provenance_graph.get("graph_sha256")
        ),
        "safety_valid": safety["valid"],
    }
    return {
        "valid": all(checks.values()),
        "checks": checks,
        "safety": safety,
        "reason": None if all(checks.values()) else "promotion_binding_invalid",
    }


def freeze_stable_dataset_manifest(
    *,
    candidate_manifest: Mapping[str, Any],
    promotion_receipt: Mapping[str, Any],
    provenance_graph: Mapping[str, Any],
    citation: Mapping[str, Any],
) -> dict:
    validation = validate_promotion_bindings(
        candidate_manifest=candidate_manifest,
        promotion_receipt=promotion_receipt,
        provenance_graph=provenance_graph,
        citation=citation,
    )
    if not validation["valid"]:
        raise ValueError(validation)

    core = {
        "schema": STABLE_DATASET_SCHEMA,
        "stable_profile": "MMRF-PUBLIC-RESEARCH-1.0",
        "dataset_id": candidate_manifest["dataset_id"],
        "schema_version": "1.0",
        "logical_schema_source": "0.9",
        "source_candidate_manifest_sha256": candidate_manifest[
            "manifest_sha256"
        ],
        "source_manifest_sha256": candidate_manifest[
            "source_manifest_sha256"
        ],
        "migration_profile": candidate_manifest["migration_profile"],
        "generation": candidate_manifest["generation"],
        "limit_exclusive": candidate_manifest["limit_exclusive"],
        "shard_size": candidate_manifest["shard_size"],
        "shard_count": candidate_manifest["shard_count"],
        "prime_count": candidate_manifest["prime_count"],
        "columnar_format": candidate_manifest["columnar_format"],
        "column_order": candidate_manifest["column_order"],
        "cid_semantics": (
            "MMRF-NPZ-COLUMNAR-0.9 logical canonical column content"
        ),
        "shards": [
            {
                **dict(shard),
                "file_path": (
                    "stable_data/shards/"
                    + Path(shard["file_path"]).name
                ),
            }
            for shard in candidate_manifest["shards"]
        ],
        "governance": {
            "promotion_receipt_sha256": promotion_receipt[
                "receipt_sha256"
            ],
            "proposal_id": promotion_receipt["proposal_id"],
            "approval_threshold": promotion_receipt[
                "approval_threshold"
            ],
            "approval_count": promotion_receipt["approval_count"],
            "reviewers": promotion_receipt["reviewers"],
        },
        "provenance_graph_sha256": provenance_graph["graph_sha256"],
        "citation_id": citation["citation_id"],
        "citation_sha256": citation["citation_sha256"],
        "safety": candidate_manifest["safety"],
        "frozen_semantics": FROZEN_SEMANTICS,
        "created_at": utc_now(),
    }
    return {
        **core,
        "manifest_sha256": sha256_json(core),
    }


def validate_stable_dataset_manifest(
    manifest: Mapping[str, Any],
    *,
    project_root: Optional[Path] = None,
    verify_shards: bool = False,
) -> dict:
    core = {
        key: value
        for key, value in manifest.items()
        if key != "manifest_sha256"
    }
    safety = validate_safety(manifest.get("safety", {}))
    checks = {
        "schema_ok": manifest.get("schema") == STABLE_DATASET_SCHEMA,
        "schema_version_ok": manifest.get("schema_version") == "1.0",
        "stable_profile_ok": (
            manifest.get("stable_profile")
            == "MMRF-PUBLIC-RESEARCH-1.0"
        ),
        "manifest_hash_ok": (
            manifest.get("manifest_sha256") == sha256_json(core)
        ),
        "cid_semantics_frozen": (
            manifest.get("cid_semantics")
            == "MMRF-NPZ-COLUMNAR-0.9 logical canonical column content"
        ),
        "frozen_semantics_ok": (
            manifest.get("frozen_semantics") == FROZEN_SEMANTICS
        ),
        "safety_ok": safety["valid"],
        "reviewer_quorum_ok": (
            int(manifest.get("governance", {}).get("approval_count", 0))
            >= int(
                manifest.get("governance", {}).get(
                    "approval_threshold",
                    2,
                )
            )
            >= 2
        ),
        "reviewers_distinct": (
            len(
                set(
                    manifest.get("governance", {}).get(
                        "reviewers",
                        [],
                    )
                )
            )
            == len(
                manifest.get("governance", {}).get(
                    "reviewers",
                    [],
                )
            )
            >= 2
        ),
    }
    shard_results = []
    if verify_shards:
        if project_root is None:
            raise ValueError("project_root_required_for_shard_verification")
        for shard in manifest.get("shards", []):
            path = Path(project_root) / shard["file_path"]
            if not path.exists():
                shard_results.append({
                    "shard_index": shard["shard_index"],
                    "valid": False,
                    "reason": "missing",
                })
                continue
            actual = file_sha256(path)
            valid = actual == shard["file_sha256"]
            shard_results.append({
                "shard_index": shard["shard_index"],
                "valid": valid,
                "expected_file_sha256": shard["file_sha256"],
                "actual_file_sha256": actual,
                "reason": None if valid else "file_hash_mismatch",
            })
    return {
        "valid": (
            all(checks.values())
            and all(item["valid"] for item in shard_results)
        ),
        "checks": checks,
        "safety": safety,
        "shards": shard_results,
        "reason": (
            None
            if all(checks.values())
            and all(item["valid"] for item in shard_results)
            else "stable_manifest_invalid"
        ),
    }


def detect_manifest_version(manifest: Mapping[str, Any]) -> str:
    schema = manifest.get("schema")
    if schema == "mmrf-data-lake-manifest-0.8":
        return "0.8"
    if schema == "mmrf-data-lake-manifest-0.9":
        return "0.9"
    if schema == STABLE_DATASET_SCHEMA:
        return "1.0"
    return "unknown"


def plan_upgrade(manifest: Mapping[str, Any]) -> dict:
    version = detect_manifest_version(manifest)
    if version == "0.8":
        return {
            "source_version": version,
            "eligible_for_direct_freeze": False,
            "actions": [
                "run MMRF-SCHEMA-0.8-TO-0.9 migration",
                "verify all migrated logical CIDs",
                "submit signed dataset proposal",
                "obtain at least two distinct approvals",
                "publish promotion receipt, provenance graph and citation",
                "freeze stable manifest 1.0",
            ],
        }
    if version == "0.9":
        return {
            "source_version": version,
            "eligible_for_direct_freeze": True,
            "actions": [
                "verify promotion receipt",
                "verify provenance DAG",
                "verify citation bindings",
                "freeze stable manifest 1.0 without rewriting shards",
            ],
        }
    if version == "1.0":
        return {
            "source_version": version,
            "eligible_for_direct_freeze": False,
            "actions": ["verify existing stable manifest"],
        }
    return {
        "source_version": version,
        "eligible_for_direct_freeze": False,
        "actions": ["unsupported manifest; manual review required"],
    }


def validate_controlled_authorization(path: Path) -> dict:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        now = datetime.now(timezone.utc)
        issued = datetime.fromisoformat(document["issued_at"])
        expires = datetime.fromisoformat(document["expires_at"])
        if issued.tzinfo is None or expires.tzinfo is None:
            raise ValueError("timezone_required")
        checks = {
            "schema_ok": (
                document.get("schema")
                == "mmrf-controlled-install-authorization-1.0"
            ),
            "allow_true": (
                document.get("allow_controlled_components") is True
            ),
            "approval_reference_present": bool(
                str(document.get("approval_reference", "")).strip()
            ),
            "profile_allowed": (
                "controlled-research"
                in set(document.get("approved_profiles", []))
            ),
            "time_valid": issued <= now <= expires,
        }
        return {
            "valid": all(checks.values()),
            "checks": checks,
            "reason": (
                None
                if all(checks.values())
                else "controlled_authorization_invalid"
            ),
        }
    except Exception as exc:
        return {
            "valid": False,
            "checks": {},
            "reason": f"controlled_authorization_error:{type(exc).__name__}",
        }


PROFILE_PATHS = {
    "public-research": [
        "mmrf_stable",
        "lake",
        "federation",
        "stable_data",
        "config/public-research.json",
        "schemas_v08",
        "schemas_v09",
        "schemas_v10",
        "docs_v08",
        "docs_v09",
        "docs_v10",
        "query_examples",
        "workflows/prime-distribution-baseline.workflow.json",
        "citations/dataset_citation_v09.json",
        "provenance/provenance_graph_v09.json",
        "results_v09/promotion_receipt_v09.json",
    ],
    "controlled-research": [
        "vault",
        "plane",
        "network",
        "docs",
        "docs_v06",
        "docs_v07",
        "schemas",
        "schemas_v06",
        "schemas_v07",
    ],
}


def _copy_entry(source_root: Path, target_root: Path, relative: str) -> None:
    source = source_root / relative
    target = target_root / relative
    if source.is_dir():
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            source,
            target,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                "*private*",
                "*recovery-share*",
            ),
        )
    elif source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    else:
        raise FileNotFoundError(source)


def installation_inventory(target_root: Path) -> dict[str, str]:
    inventory = {}
    for path in sorted(Path(target_root).rglob("*")):
        if not path.is_file():
            continue
        relative = str(path.relative_to(target_root)).replace("\\", "/")
        if relative == ".mmrf_installation.json":
            continue
        inventory[relative] = file_sha256(path)
    return inventory


def install_release(
    *,
    source_root: Path,
    target_root: Path,
    profile: str,
    controlled_authorization: Optional[Path] = None,
    force: bool = False,
) -> dict:
    source_root = Path(source_root).resolve()
    target_root = Path(target_root).resolve()
    if profile not in PROFILE_PATHS:
        raise ValueError("unknown_install_profile")
    if profile == "controlled-research":
        if controlled_authorization is None:
            raise PermissionError("controlled_authorization_required")
        authorization = validate_controlled_authorization(
            controlled_authorization
        )
        if not authorization["valid"]:
            raise PermissionError(authorization)
    else:
        authorization = None

    if target_root.exists() and any(target_root.iterdir()):
        if not force:
            raise FileExistsError("installation_target_not_empty")
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True, exist_ok=True)

    selected_profiles = ["public-research"]
    if profile == "controlled-research":
        selected_profiles.append("controlled-research")
    copied = []
    for selected in selected_profiles:
        for relative in PROFILE_PATHS[selected]:
            if relative in copied:
                continue
            _copy_entry(source_root, target_root, relative)
            copied.append(relative)

    inventory = installation_inventory(target_root)
    state_core = {
        "schema": "mmrf-installation-state-1.0",
        "release_id": STABLE_RELEASE_ID,
        "version": STABLE_VERSION,
        "profile": profile,
        "selected_profiles": selected_profiles,
        "source_release_manifest_sha256": json.loads(
            (
                source_root
                / "release_v10"
                / "stable_release_manifest_v1.0.json"
            ).read_text(encoding="utf-8")
        )["document_sha256"],
        "controlled_authorization_sha256": (
            file_sha256(controlled_authorization)
            if controlled_authorization is not None
            else None
        ),
        "installed_at": utc_now(),
        "file_count": len(inventory),
        "inventory": inventory,
    }
    state = {
        **state_core,
        "installation_state_sha256": sha256_json(state_core),
    }
    (target_root / ".mmrf_installation.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return state


def verify_installation(target_root: Path) -> dict:
    target_root = Path(target_root)
    state_path = target_root / ".mmrf_installation.json"
    if not state_path.exists():
        return {"valid": False, "reason": "installation_state_missing"}
    state = json.loads(state_path.read_text(encoding="utf-8"))
    core = {
        key: value
        for key, value in state.items()
        if key != "installation_state_sha256"
    }
    checks = {
        "state_hash_ok": (
            state.get("installation_state_sha256")
            == sha256_json(core)
        ),
        "release_id_ok": state.get("release_id") == STABLE_RELEASE_ID,
        "version_ok": state.get("version") == STABLE_VERSION,
    }
    mismatches = []
    for relative, expected in state.get("inventory", {}).items():
        path = target_root / relative
        if not path.exists():
            mismatches.append({
                "path": relative,
                "reason": "missing",
            })
            continue
        actual = file_sha256(path)
        if actual != expected:
            mismatches.append({
                "path": relative,
                "reason": "hash_mismatch",
                "expected": expected,
                "actual": actual,
            })
    checks["inventory_ok"] = not mismatches
    return {
        "valid": all(checks.values()),
        "checks": checks,
        "mismatches": mismatches,
        "profile": state.get("profile"),
        "file_count": state.get("file_count"),
        "reason": None if all(checks.values()) else "installation_invalid",
    }


def build_release_payload_checksums(
    root: Path,
    *,
    excluded_prefixes: Sequence[str] = (),
) -> dict[str, str]:
    root = Path(root)
    result = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        relative = str(path.relative_to(root)).replace("\\", "/")
        if any(
            relative == prefix
            or relative.startswith(prefix.rstrip("/") + "/")
            for prefix in excluded_prefixes
        ):
            continue
        result[relative] = file_sha256(path)
    return result


def verify_release(
    *,
    release_root: Path,
    manifest_path: Path,
    public_key_path: Path,
    verify_payload: bool = True,
) -> dict:
    release_root = Path(release_root)
    manifest = json.loads(
        Path(manifest_path).read_text(encoding="utf-8")
    )
    signature = verify_signed_release_document(
        manifest,
        public_key_path,
    )
    checks = {
        "signature_and_document_hash": signature["valid"],
        "schema_ok": (
            manifest.get("schema") == RELEASE_MANIFEST_SCHEMA
        ),
        "release_id_ok": (
            manifest.get("release_id") == STABLE_RELEASE_ID
        ),
        "version_ok": manifest.get("version") == STABLE_VERSION,
        "safety_ok": validate_safety(
            manifest.get("safety", {})
        )["valid"],
    }
    mismatches = []
    if verify_payload:
        for relative, expected in manifest.get(
            "payload_checksums",
            {}
        ).items():
            path = release_root / relative
            if not path.exists():
                mismatches.append({
                    "path": relative,
                    "reason": "missing",
                })
                continue
            actual = file_sha256(path)
            if actual != expected:
                mismatches.append({
                    "path": relative,
                    "reason": "hash_mismatch",
                    "expected": expected,
                    "actual": actual,
                })
    checks["payload_ok"] = not mismatches
    return {
        "valid": all(checks.values()),
        "checks": checks,
        "signature": signature,
        "mismatches": mismatches,
        "reason": None if all(checks.values()) else "release_invalid",
    }


def doctor(project_root: Path) -> dict:
    project_root = Path(project_root)
    dependencies = {}
    for name in ("numpy", "cryptography"):
        try:
            module = __import__(name)
            dependencies[name] = {
                "available": True,
                "version": getattr(module, "__version__", "unknown"),
            }
        except Exception as exc:
            dependencies[name] = {
                "available": False,
                "reason": f"{type(exc).__name__}:{exc}",
            }
    stable_manifest_path = (
        project_root / "stable_data" / "stable_manifest_v1.0.json"
    )
    manifest_status = None
    if stable_manifest_path.exists():
        manifest = json.loads(
            stable_manifest_path.read_text(encoding="utf-8")
        )
        manifest_status = validate_stable_dataset_manifest(
            manifest,
            project_root=project_root,
            verify_shards=True,
        )
    private_markers = []
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        lower = str(path.relative_to(project_root)).lower()
        if (
            "private_material" in lower
            or lower.endswith(".private.pem")
            or "recovery-share" in lower
        ):
            private_markers.append(lower)
    return {
        "schema": "mmrf-doctor-report-1.0",
        "release_id": STABLE_RELEASE_ID,
        "python": {
            "version": sys.version,
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
        },
        "dependencies": dependencies,
        "stable_manifest": manifest_status,
        "private_material_markers": private_markers,
        "valid": (
            all(item["available"] for item in dependencies.values())
            and manifest_status is not None
            and manifest_status["valid"]
            and not private_markers
        ),
        "created_at": utc_now(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="mmrf")
    parser.add_argument(
        "--project-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify-release")
    verify.add_argument("--manifest")
    verify.add_argument("--public-key")

    install = sub.add_parser("install")
    install.add_argument("--target", required=True)
    install.add_argument(
        "--profile",
        choices=sorted(PROFILE_PATHS),
        default="public-research",
    )
    install.add_argument("--controlled-authorization")
    install.add_argument("--force", action="store_true")

    verify_install = sub.add_parser("verify-installation")
    verify_install.add_argument("--target", required=True)

    upgrade = sub.add_parser("plan-upgrade")
    upgrade.add_argument("--manifest", required=True)

    doctor_parser = sub.add_parser("doctor")

    args = parser.parse_args()
    project_root = Path(args.project_root)

    if args.command == "verify-release":
        manifest = Path(args.manifest) if args.manifest else (
            project_root
            / "release_v10"
            / "stable_release_manifest_v1.0.json"
        )
        public_key = Path(args.public_key) if args.public_key else (
            project_root
            / "release_v10"
            / "stable_release_signing.public.pem"
        )
        result = verify_release(
            release_root=project_root,
            manifest_path=manifest,
            public_key_path=public_key,
        )
    elif args.command == "install":
        result = install_release(
            source_root=project_root,
            target_root=Path(args.target),
            profile=args.profile,
            controlled_authorization=(
                Path(args.controlled_authorization)
                if args.controlled_authorization
                else None
            ),
            force=args.force,
        )
    elif args.command == "verify-installation":
        result = verify_installation(Path(args.target))
    elif args.command == "plan-upgrade":
        manifest = json.loads(
            Path(args.manifest).read_text(encoding="utf-8")
        )
        result = plan_upgrade(manifest)
    else:
        result = doctor(project_root)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.get("valid", True) else 1)


if __name__ == "__main__":
    main()
