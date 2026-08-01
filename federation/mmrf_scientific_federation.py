from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import numpy as np
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


V08_COLUMNS = (
    "prime",
    "ordinal",
    "bit_length",
    "decimal_digits",
    "previous_gap",
    "residue_6",
    "residue_30",
    "residue_210",
    "family_flags",
)

V09_COLUMNS = V08_COLUMNS + ("wheel30_class",)

WHEEL30_CLASSES = {
    1: 0,
    7: 1,
    11: 2,
    13: 3,
    17: 4,
    19: 5,
    23: 6,
    29: 7,
}

FORBIDDEN_SAFETY_TRUE = {
    "source_factor_relations",
    "rsa_target_endpoint",
    "factor_candidate_endpoint",
    "range_narrowing_endpoint",
    "exact_prime_list_endpoint",
    "raw_factor_export",
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


def generate_signing_keypair(
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


def sign_document(
    core: Mapping[str, Any],
    private_key_path: Path,
) -> dict:
    signature = load_private(private_key_path).sign(
        canonical_json(core).encode("utf-8")
    )
    signed = {**dict(core), "signature_ed25519": b64(signature)}
    return {**signed, "document_sha256": sha256_json(signed)}


def verify_document(
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
            "hash_ok": document.get("document_sha256") == sha256_json(signed),
            "signature_ok": True,
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


def create_catalog_announcement(
    *,
    node_id: str,
    catalog_version: int,
    dataset_manifest_sha256: str,
    shard_records: Sequence[Mapping[str, Any]],
    private_key_path: Path,
    previous_announcement_sha256: str = "0" * 64,
) -> dict:
    records = sorted(
        [
            {
                "shard_index": int(item["shard_index"]),
                "cid": item["cid"],
                "file_sha256": item["file_sha256"],
                "content_sha256": item["content_sha256"],
                "row_count": int(item["row_count"]),
            }
            for item in shard_records
        ],
        key=lambda item: item["shard_index"],
    )
    core = {
        "schema": "mmrf-shard-catalog-announcement-0.9",
        "node_id": node_id,
        "catalog_version": int(catalog_version),
        "dataset_manifest_sha256": dataset_manifest_sha256,
        "previous_announcement_sha256": previous_announcement_sha256,
        "shard_count": len(records),
        "shards": records,
        "created_at": utc_now(),
    }
    return sign_document(core, private_key_path)


class FederationCatalog:
    def __init__(
        self,
        db_path: Path,
        trusted_node_keys: Mapping[str, Path],
    ):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.trusted_node_keys = {
            node_id: Path(path)
            for node_id, path in trusted_node_keys.items()
        }
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS announcements(
                node_id TEXT NOT NULL,
                catalog_version INTEGER NOT NULL,
                dataset_manifest_sha256 TEXT NOT NULL,
                announcement_sha256 TEXT NOT NULL UNIQUE,
                document_json TEXT NOT NULL,
                accepted_at TEXT NOT NULL,
                PRIMARY KEY(node_id, catalog_version)
            );

            CREATE TABLE IF NOT EXISTS current_nodes(
                node_id TEXT PRIMARY KEY,
                catalog_version INTEGER NOT NULL,
                announcement_sha256 TEXT NOT NULL,
                dataset_manifest_sha256 TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def ingest(self, announcement: Mapping[str, Any]) -> dict:
        node_id = str(announcement.get("node_id"))
        if node_id not in self.trusted_node_keys:
            return {"accepted": False, "reason": "untrusted_node"}
        verification = verify_document(
            announcement,
            self.trusted_node_keys[node_id],
        )
        if not verification["valid"]:
            return {
                "accepted": False,
                "reason": verification["reason"],
            }
        if announcement.get("schema") != "mmrf-shard-catalog-announcement-0.9":
            return {"accepted": False, "reason": "schema_mismatch"}

        current = self.conn.execute(
            "SELECT * FROM current_nodes WHERE node_id = ?",
            (node_id,),
        ).fetchone()
        if current is None:
            if int(announcement["catalog_version"]) != 1:
                return {
                    "accepted": False,
                    "reason": "first_catalog_version_must_be_one",
                }
            if announcement["previous_announcement_sha256"] != "0" * 64:
                return {
                    "accepted": False,
                    "reason": "first_catalog_previous_hash_invalid",
                }
        else:
            expected_version = int(current["catalog_version"]) + 1
            if int(announcement["catalog_version"]) < expected_version:
                existing = self.conn.execute(
                    """
                    SELECT announcement_sha256
                    FROM announcements
                    WHERE node_id = ? AND catalog_version = ?
                    """,
                    (
                        node_id,
                        int(announcement["catalog_version"]),
                    ),
                ).fetchone()
                if (
                    existing
                    and existing["announcement_sha256"]
                    != announcement["document_sha256"]
                ):
                    return {
                        "accepted": False,
                        "reason": "same_version_split_catalog",
                    }
                return {"accepted": False, "reason": "stale_catalog_version"}
            if int(announcement["catalog_version"]) != expected_version:
                return {"accepted": False, "reason": "catalog_version_gap"}
            if (
                announcement["previous_announcement_sha256"]
                != current["announcement_sha256"]
            ):
                return {
                    "accepted": False,
                    "reason": "catalog_chain_mismatch",
                }

        self.conn.execute(
            """
            INSERT INTO announcements(
                node_id, catalog_version,
                dataset_manifest_sha256,
                announcement_sha256,
                document_json, accepted_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                node_id,
                int(announcement["catalog_version"]),
                announcement["dataset_manifest_sha256"],
                announcement["document_sha256"],
                canonical_json(announcement),
                utc_now(),
            ),
        )
        self.conn.execute(
            """
            INSERT OR REPLACE INTO current_nodes(
                node_id, catalog_version,
                announcement_sha256,
                dataset_manifest_sha256
            ) VALUES (?, ?, ?, ?)
            """,
            (
                node_id,
                int(announcement["catalog_version"]),
                announcement["document_sha256"],
                announcement["dataset_manifest_sha256"],
            ),
        )
        self.conn.commit()
        return {
            "accepted": True,
            "node_id": node_id,
            "catalog_version": int(announcement["catalog_version"]),
            "announcement_sha256": announcement["document_sha256"],
        }

    def current_announcements(self) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT a.document_json
            FROM announcements a
            JOIN current_nodes c
              ON c.node_id = a.node_id
             AND c.catalog_version = a.catalog_version
            ORDER BY a.node_id
            """
        )
        return [json.loads(row["document_json"]) for row in rows]

    def coverage(
        self,
        *,
        expected_manifest_sha256: str,
        expected_shards: Sequence[Mapping[str, Any]],
        minimum_replication: int,
    ) -> dict:
        expected = {
            item["cid"]: {
                "shard_index": int(item["shard_index"]),
                "file_sha256": item["file_sha256"],
                "content_sha256": item["content_sha256"],
            }
            for item in expected_shards
        }
        holders: dict[str, list[str]] = {
            cid: [] for cid in expected
        }
        conflicts: list[dict] = []
        manifest_mismatch_nodes = []
        for announcement in self.current_announcements():
            if announcement["dataset_manifest_sha256"] != expected_manifest_sha256:
                manifest_mismatch_nodes.append(announcement["node_id"])
                continue
            for shard in announcement["shards"]:
                cid = shard["cid"]
                if cid not in expected:
                    conflicts.append({
                        "node_id": announcement["node_id"],
                        "cid": cid,
                        "reason": "unexpected_cid",
                    })
                    continue
                if (
                    shard["file_sha256"] != expected[cid]["file_sha256"]
                    or shard["content_sha256"] != expected[cid]["content_sha256"]
                ):
                    conflicts.append({
                        "node_id": announcement["node_id"],
                        "cid": cid,
                        "reason": "shard_hash_conflict",
                    })
                    continue
                holders[cid].append(announcement["node_id"])

        replication = {
            cid: len(set(nodes))
            for cid, nodes in holders.items()
        }
        under_replicated = [
            {
                "cid": cid,
                "shard_index": expected[cid]["shard_index"],
                "replicas": replication[cid],
                "holders": sorted(set(holders[cid])),
            }
            for cid in sorted(
                expected,
                key=lambda value: expected[value]["shard_index"],
            )
            if replication[cid] < minimum_replication
        ]
        return {
            "valid": (
                not conflicts
                and not manifest_mismatch_nodes
                and not under_replicated
            ),
            "minimum_replication": minimum_replication,
            "expected_shard_count": len(expected),
            "node_count": len(self.current_announcements()),
            "replication": replication,
            "under_replicated": under_replicated,
            "conflicts": conflicts,
            "manifest_mismatch_nodes": sorted(manifest_mismatch_nodes),
        }


def canonical_array_content_sha256(
    arrays: Mapping[str, np.ndarray],
    columns: Sequence[str],
    profile: str,
) -> str:
    digest = hashlib.sha256()
    digest.update(profile.encode("ascii") + b"\0")
    for name in columns:
        array = np.ascontiguousarray(arrays[name])
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(str(array.dtype).encode("ascii") + b"\0")
        digest.update(
            canonical_json(list(array.shape)).encode("ascii")
        )
        digest.update(b"\0")
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def migrate_v08_shard_to_v09(
    *,
    source_path: Path,
    source_record: Mapping[str, Any],
    output_dir: Path,
) -> dict:
    started = time.perf_counter_ns()
    with np.load(source_path, allow_pickle=False) as archive:
        arrays = {
            column: archive[column]
            for column in V08_COLUMNS
        }
    residue_30 = arrays["residue_30"]
    wheel_class = np.full(
        len(residue_30),
        255,
        dtype=np.uint8,
    )
    for residue, class_id in WHEEL30_CLASSES.items():
        wheel_class[residue_30 == residue] = class_id
    migrated = {**arrays, "wheel30_class": wheel_class}
    content_sha = canonical_array_content_sha256(
        migrated,
        V09_COLUMNS,
        "MMRF-NPZ-COLUMNAR-0.9",
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = (
        f"shard_{int(source_record['shard_index']):06d}_"
        f"{content_sha[:16]}.npz"
    )
    output_path = output_dir / filename
    np.savez_compressed(output_path, **migrated)
    migration_record = {
        "schema": "mmrf-shard-migration-record-0.9",
        "migration_id": f"migration:{uuid.uuid4()}",
        "migration_profile": "MMRF-SCHEMA-0.8-TO-0.9",
        "source_cid": source_record["cid"],
        "source_file_sha256": source_record["file_sha256"],
        "target_cid": f"mmrf-shard:{content_sha}",
        "target_file_sha256": file_sha256(output_path),
        "target_content_sha256": content_sha,
        "shard_index": int(source_record["shard_index"]),
        "row_count": int(source_record["row_count"]),
        "added_column": "wheel30_class",
        "source_columns": list(V08_COLUMNS),
        "target_columns": list(V09_COLUMNS),
        "output_path": str(output_path),
        "elapsed_ms": (
            time.perf_counter_ns() - started
        ) / 1_000_000,
    }
    return migration_record


def migrate_manifest_v08_to_v09(
    *,
    source_manifest: Mapping[str, Any],
    project_root: Path,
    output_dir: Path,
    manifest_path: Path,
) -> dict:
    records = []
    for shard in source_manifest["shards"]:
        source_path = Path(project_root) / shard["file_path"]
        records.append(
            migrate_v08_shard_to_v09(
                source_path=source_path,
                source_record=shard,
                output_dir=output_dir,
            )
        )
    manifest_core = {
        "schema": "mmrf-data-lake-manifest-0.9",
        "dataset_id": source_manifest["dataset_id"],
        "schema_version": "0.9",
        "generation": source_manifest["generation"],
        "limit_exclusive": source_manifest["limit_exclusive"],
        "shard_size": source_manifest["shard_size"],
        "shard_count": len(records),
        "prime_count": source_manifest["prime_count"],
        "columnar_format": "NPZ_COMPRESSED_COLUMNS",
        "column_order": list(V09_COLUMNS),
        "source_manifest_sha256": source_manifest["manifest_sha256"],
        "migration_profile": "MMRF-SCHEMA-0.8-TO-0.9",
        "shards": [
            {
                "shard_index": item["shard_index"],
                "cid": item["target_cid"],
                "source_cid": item["source_cid"],
                "row_count": item["row_count"],
                "file_path": str(
                    Path("federation_data")
                    / "migrated_v09"
                    / "shards"
                    / Path(item["output_path"]).name
                ),
                "file_sha256": item["target_file_sha256"],
                "content_sha256": item["target_content_sha256"],
            }
            for item in records
        ],
        "safety": {
            "classification": "L0_PUBLIC_MATH",
            "source_factor_relations": False,
            "rsa_target_endpoint": False,
            "factor_candidate_endpoint": False,
            "range_narrowing_endpoint": False,
            "exact_prime_list_endpoint": False,
            "raw_factor_export": False,
        },
        "created_at": utc_now(),
    }
    manifest = {
        **manifest_core,
        "manifest_sha256": sha256_json(manifest_core),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "manifest": manifest,
        "records": records,
        "manifest_path": str(manifest_path),
    }


def verify_migrated_manifest(
    *,
    manifest: Mapping[str, Any],
    project_root: Path,
) -> dict:
    checks = {
        "schema_ok": manifest.get("schema") == "mmrf-data-lake-manifest-0.9",
        "columns_ok": tuple(manifest.get("column_order", [])) == V09_COLUMNS,
        "safety_ok": all(
            manifest.get("safety", {}).get(key) is False
            for key in FORBIDDEN_SAFETY_TRUE
        ),
    }
    shard_results = []
    for shard in manifest.get("shards", []):
        path = Path(project_root) / shard["file_path"]
        if not path.exists():
            shard_results.append({
                "shard_index": shard["shard_index"],
                "valid": False,
                "reason": "missing",
            })
            continue
        if file_sha256(path) != shard["file_sha256"]:
            shard_results.append({
                "shard_index": shard["shard_index"],
                "valid": False,
                "reason": "file_hash_mismatch",
            })
            continue
        with np.load(path, allow_pickle=False) as archive:
            arrays = {
                column: archive[column]
                for column in V09_COLUMNS
            }
        content_sha = canonical_array_content_sha256(
            arrays,
            V09_COLUMNS,
            "MMRF-NPZ-COLUMNAR-0.9",
        )
        local_checks = {
            "content_hash_ok": content_sha == shard["content_sha256"],
            "cid_ok": shard["cid"] == f"mmrf-shard:{content_sha}",
            "row_count_ok": len(arrays["prime"]) == int(shard["row_count"]),
            "wheel_class_valid": bool(
                np.all(
                    (arrays["wheel30_class"] <= 7)
                    | (arrays["wheel30_class"] == 255)
                )
            ),
        }
        shard_results.append({
            "shard_index": shard["shard_index"],
            "valid": all(local_checks.values()),
            "checks": local_checks,
            "reason": None if all(local_checks.values()) else "content_mismatch",
        })
    core = {
        key: value
        for key, value in manifest.items()
        if key != "manifest_sha256"
    }
    checks["manifest_hash_ok"] = (
        manifest.get("manifest_sha256") == sha256_json(core)
    )
    return {
        "valid": all(checks.values())
        and all(item["valid"] for item in shard_results),
        "checks": checks,
        "shards": shard_results,
    }


def create_dataset_proposal(
    *,
    proposal_id: str,
    proposer_id: str,
    base_manifest_sha256: str,
    candidate_manifest: Mapping[str, Any],
    migration_profile: str,
    purpose: str,
    private_key_path: Path,
) -> dict:
    core = {
        "schema": "mmrf-dataset-proposal-0.9",
        "proposal_id": proposal_id,
        "proposer_id": proposer_id,
        "base_manifest_sha256": base_manifest_sha256,
        "candidate_manifest_sha256": candidate_manifest["manifest_sha256"],
        "candidate_schema_version": candidate_manifest.get(
            "schema_version",
            "unknown",
        ),
        "migration_profile": migration_profile,
        "purpose": purpose,
        "safety": candidate_manifest["safety"],
        "provenance_inputs": [
            base_manifest_sha256,
            candidate_manifest["manifest_sha256"],
        ],
        "created_at": utc_now(),
    }
    return sign_document(core, private_key_path)


def create_review(
    *,
    proposal: Mapping[str, Any],
    reviewer_id: str,
    decision: str,
    findings: Sequence[str],
    private_key_path: Path,
) -> dict:
    if decision not in {"APPROVE", "REJECT"}:
        raise ValueError("invalid review decision")
    core = {
        "schema": "mmrf-dataset-review-0.9",
        "review_id": f"review:{uuid.uuid4()}",
        "proposal_id": proposal["proposal_id"],
        "proposal_sha256": proposal["document_sha256"],
        "reviewer_id": reviewer_id,
        "decision": decision,
        "findings": list(findings),
        "created_at": utc_now(),
    }
    return sign_document(core, private_key_path)


def safety_gate(proposal: Mapping[str, Any]) -> dict:
    safety = proposal.get("safety", {})
    unsafe = [
        key
        for key in sorted(FORBIDDEN_SAFETY_TRUE)
        if safety.get(key) is not False
    ]
    return {
        "passed": not unsafe
        and safety.get("classification") == "L0_PUBLIC_MATH",
        "unsafe_fields": unsafe,
        "classification": safety.get("classification"),
    }


class GovernanceStore:
    def __init__(
        self,
        db_path: Path,
        proposer_keys: Mapping[str, Path],
        reviewer_keys: Mapping[str, Path],
        approval_threshold: int = 2,
    ):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.proposer_keys = {
            key: Path(value) for key, value in proposer_keys.items()
        }
        self.reviewer_keys = {
            key: Path(value) for key, value in reviewer_keys.items()
        }
        self.approval_threshold = int(approval_threshold)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS proposals(
                proposal_id TEXT PRIMARY KEY,
                proposal_sha256 TEXT NOT NULL UNIQUE,
                document_json TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                promoted_at TEXT
            );

            CREATE TABLE IF NOT EXISTS reviews(
                review_id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL,
                reviewer_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                review_sha256 TEXT NOT NULL UNIQUE,
                document_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(proposal_id, reviewer_id)
            );

            CREATE TABLE IF NOT EXISTS promotions(
                promotion_id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL UNIQUE,
                candidate_manifest_sha256 TEXT NOT NULL,
                approval_count INTEGER NOT NULL,
                receipt_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def submit(self, proposal: Mapping[str, Any]) -> dict:
        proposer = str(proposal.get("proposer_id"))
        if proposer not in self.proposer_keys:
            return {"accepted": False, "reason": "unknown_proposer"}
        verification = verify_document(
            proposal,
            self.proposer_keys[proposer],
        )
        if not verification["valid"]:
            return {"accepted": False, "reason": verification["reason"]}
        gate = safety_gate(proposal)
        if not gate["passed"]:
            return {
                "accepted": False,
                "reason": "safety_gate_failed",
                "gate": gate,
            }
        self.conn.execute(
            """
            INSERT INTO proposals(
                proposal_id, proposal_sha256,
                document_json, state, created_at
            ) VALUES (?, ?, ?, 'UNDER_REVIEW', ?)
            """,
            (
                proposal["proposal_id"],
                proposal["document_sha256"],
                canonical_json(proposal),
                proposal["created_at"],
            ),
        )
        self.conn.commit()
        return {
            "accepted": True,
            "state": "UNDER_REVIEW",
            "proposal_id": proposal["proposal_id"],
        }

    def add_review(self, review: Mapping[str, Any]) -> dict:
        reviewer = str(review.get("reviewer_id"))
        if reviewer not in self.reviewer_keys:
            return {"accepted": False, "reason": "unknown_reviewer"}
        verification = verify_document(
            review,
            self.reviewer_keys[reviewer],
        )
        if not verification["valid"]:
            return {"accepted": False, "reason": verification["reason"]}
        proposal = self.conn.execute(
            "SELECT * FROM proposals WHERE proposal_id = ?",
            (review["proposal_id"],),
        ).fetchone()
        if proposal is None:
            return {"accepted": False, "reason": "proposal_not_found"}
        if review["proposal_sha256"] != proposal["proposal_sha256"]:
            return {"accepted": False, "reason": "proposal_binding_mismatch"}
        try:
            self.conn.execute(
                """
                INSERT INTO reviews(
                    review_id, proposal_id, reviewer_id,
                    decision, review_sha256,
                    document_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review["review_id"],
                    review["proposal_id"],
                    reviewer,
                    review["decision"],
                    review["document_sha256"],
                    canonical_json(review),
                    review["created_at"],
                ),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            return {"accepted": False, "reason": "duplicate_reviewer"}
        return {
            "accepted": True,
            "proposal_id": review["proposal_id"],
            "reviewer_id": reviewer,
            "decision": review["decision"],
        }

    def status(self, proposal_id: str) -> dict:
        proposal = self.conn.execute(
            "SELECT * FROM proposals WHERE proposal_id = ?",
            (proposal_id,),
        ).fetchone()
        if proposal is None:
            raise KeyError(proposal_id)
        reviews = [
            dict(row)
            for row in self.conn.execute(
                """
                SELECT reviewer_id, decision,
                       review_sha256, created_at
                FROM reviews
                WHERE proposal_id = ?
                ORDER BY reviewer_id
                """,
                (proposal_id,),
            )
        ]
        approvals = [
            item for item in reviews
            if item["decision"] == "APPROVE"
        ]
        rejections = [
            item for item in reviews
            if item["decision"] == "REJECT"
        ]
        return {
            "proposal_id": proposal_id,
            "state": proposal["state"],
            "approval_count": len(approvals),
            "rejection_count": len(rejections),
            "approval_threshold": self.approval_threshold,
            "reviews": reviews,
        }

    def promote(self, proposal_id: str) -> dict:
        status = self.status(proposal_id)
        if status["state"] == "PROMOTED":
            return {"promoted": True, "reason": "already_promoted"}
        if status["rejection_count"]:
            return {"promoted": False, "reason": "review_rejection_present"}
        if status["approval_count"] < self.approval_threshold:
            return {"promoted": False, "reason": "insufficient_approvals"}
        proposal_row = self.conn.execute(
            "SELECT document_json FROM proposals WHERE proposal_id = ?",
            (proposal_id,),
        ).fetchone()
        proposal = json.loads(proposal_row["document_json"])
        receipt_core = {
            "schema": "mmrf-dataset-promotion-receipt-0.9",
            "promotion_id": f"promotion:{uuid.uuid4()}",
            "proposal_id": proposal_id,
            "proposal_sha256": proposal["document_sha256"],
            "candidate_manifest_sha256": proposal[
                "candidate_manifest_sha256"
            ],
            "approval_threshold": self.approval_threshold,
            "approval_count": status["approval_count"],
            "reviewers": sorted(
                item["reviewer_id"]
                for item in status["reviews"]
                if item["decision"] == "APPROVE"
            ),
            "promoted_at": utc_now(),
        }
        receipt = {
            **receipt_core,
            "receipt_sha256": sha256_json(receipt_core),
        }
        self.conn.execute(
            """
            UPDATE proposals
            SET state = 'PROMOTED', promoted_at = ?
            WHERE proposal_id = ?
            """,
            (receipt["promoted_at"], proposal_id),
        )
        self.conn.execute(
            """
            INSERT INTO promotions(
                promotion_id, proposal_id,
                candidate_manifest_sha256,
                approval_count, receipt_json,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                receipt["promotion_id"],
                proposal_id,
                receipt["candidate_manifest_sha256"],
                receipt["approval_count"],
                canonical_json(receipt),
                receipt["promoted_at"],
            ),
        )
        self.conn.commit()
        return {"promoted": True, "receipt": receipt}


class ProvenanceGraph:
    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.edges: list[dict] = []

    def add_node(
        self,
        node_id: str,
        node_type: str,
        content_sha256: str,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        if node_id in self.nodes:
            raise ValueError("duplicate provenance node")
        self.nodes[node_id] = {
            "node_id": node_id,
            "node_type": node_type,
            "content_sha256": content_sha256,
            "metadata": dict(metadata or {}),
        }

    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
    ) -> None:
        if source not in self.nodes or target not in self.nodes:
            raise KeyError("provenance node missing")
        self.edges.append({
            "source": source,
            "target": target,
            "relation": relation,
        })

    def _is_dag(self) -> bool:
        adjacency = {node: [] for node in self.nodes}
        indegree = {node: 0 for node in self.nodes}
        for edge in self.edges:
            adjacency[edge["source"]].append(edge["target"])
            indegree[edge["target"]] += 1
        queue = sorted(
            node for node, degree in indegree.items()
            if degree == 0
        )
        visited = 0
        while queue:
            node = queue.pop(0)
            visited += 1
            for target in adjacency[node]:
                indegree[target] -= 1
                if indegree[target] == 0:
                    queue.append(target)
                    queue.sort()
        return visited == len(self.nodes)

    def document(self) -> dict:
        core = {
            "schema": "mmrf-provenance-graph-0.9",
            "nodes": [
                self.nodes[node_id]
                for node_id in sorted(self.nodes)
            ],
            "edges": sorted(
                self.edges,
                key=lambda item: (
                    item["source"],
                    item["target"],
                    item["relation"],
                ),
            ),
        }
        return {
            **core,
            "graph_sha256": sha256_json(core),
            "dag_valid": self._is_dag(),
        }


def validate_provenance_graph(graph: Mapping[str, Any]) -> dict:
    core = {
        key: value
        for key, value in graph.items()
        if key not in {"graph_sha256", "dag_valid"}
    }
    nodes = {item["node_id"] for item in graph.get("nodes", [])}
    edges_valid = all(
        edge["source"] in nodes and edge["target"] in nodes
        for edge in graph.get("edges", [])
    )
    helper = ProvenanceGraph()
    for node in graph.get("nodes", []):
        helper.add_node(
            node["node_id"],
            node["node_type"],
            node["content_sha256"],
            node.get("metadata"),
        )
    for edge in graph.get("edges", []):
        helper.add_edge(
            edge["source"],
            edge["target"],
            edge["relation"],
        )
    checks = {
        "hash_ok": graph.get("graph_sha256") == sha256_json(core),
        "edges_valid": edges_valid,
        "dag_valid": helper._is_dag(),
        "declared_dag_matches": graph.get("dag_valid") == helper._is_dag(),
    }
    return {
        "valid": all(checks.values()),
        "checks": checks,
        "reason": None if all(checks.values()) else "provenance_invalid",
    }


def create_dataset_citation(
    *,
    manifest: Mapping[str, Any],
    promotion_receipt: Mapping[str, Any],
    provenance_graph: Mapping[str, Any],
    title: str,
    publisher: str,
) -> dict:
    citation_id = (
        "MMRF-DATASET-"
        + manifest["manifest_sha256"][:16].upper()
    )
    core = {
        "schema": "mmrf-dataset-citation-0.9",
        "citation_id": citation_id,
        "title": title,
        "publisher": publisher,
        "dataset_id": manifest["dataset_id"],
        "schema_version": manifest.get("schema_version", "0.9"),
        "manifest_sha256": manifest["manifest_sha256"],
        "promotion_receipt_sha256": promotion_receipt[
            "receipt_sha256"
        ],
        "provenance_graph_sha256": provenance_graph["graph_sha256"],
        "issued_at": utc_now(),
        "preferred_citation": (
            f"{publisher}. {title}. "
            f"MMRF dataset {citation_id}; "
            f"manifest {manifest['manifest_sha256']}."
        ),
    }
    return {**core, "citation_sha256": sha256_json(core)}


def verify_dataset_citation(
    citation: Mapping[str, Any],
    *,
    manifest: Mapping[str, Any],
    promotion_receipt: Mapping[str, Any],
    provenance_graph: Mapping[str, Any],
) -> dict:
    core = {
        key: value
        for key, value in citation.items()
        if key != "citation_sha256"
    }
    checks = {
        "citation_hash_ok": citation.get("citation_sha256")
        == sha256_json(core),
        "manifest_binding_ok": citation.get("manifest_sha256")
        == manifest.get("manifest_sha256"),
        "promotion_binding_ok": citation.get(
            "promotion_receipt_sha256"
        ) == promotion_receipt.get("receipt_sha256"),
        "provenance_binding_ok": citation.get(
            "provenance_graph_sha256"
        ) == provenance_graph.get("graph_sha256"),
    }
    return {
        "valid": all(checks.values()),
        "checks": checks,
        "reason": None if all(checks.values()) else "citation_binding_invalid",
    }
