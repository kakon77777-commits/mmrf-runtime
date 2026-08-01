from __future__ import annotations

import copy
import json
import os
import shutil
import statistics
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lake"))
sys.path.insert(0, str(ROOT / "federation"))

from mmrf_stable.runtime import (
    FROZEN_SEMANTICS,
    doctor,
    install_release,
    plan_upgrade,
    validate_controlled_authorization,
    validate_stable_dataset_manifest,
    verify_installation,
    verify_release,
)
from mmrf_data_lake import DataLake, ScientificQueryGuard
from mmrf_scientific_federation import (
    validate_provenance_graph,
    verify_dataset_citation,
    verify_migrated_manifest,
)


RESULTS = ROOT / "results_v10"
RESULTS.mkdir(parents=True, exist_ok=True)

stable_manifest = json.loads(
    (
        ROOT / "stable_data" / "stable_manifest_v1.0.json"
    ).read_text(encoding="utf-8")
)
candidate_manifest = json.loads(
    (
        ROOT
        / "federation_data"
        / "migrated_v09"
        / "manifest_v09.json"
    ).read_text(encoding="utf-8")
)
v08_manifest = json.loads(
    (
        ROOT / "lake_data" / "manifests" / "current_manifest.json"
    ).read_text(encoding="utf-8")
)
promotion_receipt = json.loads(
    (
        ROOT / "results_v09" / "promotion_receipt_v09.json"
    ).read_text(encoding="utf-8")
)
provenance = json.loads(
    (
        ROOT / "provenance" / "provenance_graph_v09.json"
    ).read_text(encoding="utf-8")
)
citation = json.loads(
    (
        ROOT / "citations" / "dataset_citation_v09.json"
    ).read_text(encoding="utf-8")
)

timings = {}
checks = {}

# 1. Stable manifest and all 20 shard file hashes.
verify_times = []
stable_validation = None
for _ in range(11):
    started = time.perf_counter_ns()
    stable_validation = validate_stable_dataset_manifest(
        stable_manifest,
        project_root=ROOT,
        verify_shards=True,
    )
    verify_times.append(
        (time.perf_counter_ns() - started) / 1_000_000
    )
assert stable_validation is not None and stable_validation["valid"]
timings["stable_manifest_and_20_shards"] = {
    "median_ms": statistics.median(verify_times),
    "p90_ms": sorted(verify_times)[
        int(0.9 * (len(verify_times) - 1))
    ],
}
checks["stable_manifest_valid"] = stable_validation["valid"]
checks["all_20_stable_shards_valid"] = all(
    item["valid"] for item in stable_validation["shards"]
)
checks["stable_frozen_semantics_exact"] = (
    stable_manifest["frozen_semantics"] == FROZEN_SEMANTICS
)

# 2. v0.8 query-plane compatibility in an isolated copy.
with tempfile.TemporaryDirectory() as td:
    temp_root = Path(td)
    (temp_root / "lake_data" / "primary").mkdir(parents=True)
    (temp_root / "lake_state").mkdir(parents=True)
    shutil.copytree(
        ROOT / "lake_data" / "primary" / "shards",
        temp_root / "lake_data" / "primary" / "shards",
    )
    shutil.copytree(
        ROOT / "lake_data" / "manifests",
        temp_root / "lake_data" / "manifests",
    )
    shutil.copy2(
        ROOT / "lake_state" / "lake_index.sqlite",
        temp_root / "lake_state" / "lake_index.sqlite",
    )
    lake = DataLake(
        root_dir=temp_root / "lake_data" / "primary",
        index_db=temp_root / "lake_state" / "lake_index.sqlite",
        shard_size=100_000,
    )
    query_times = []
    density_response = None
    for repeat in range(11):
        guard = ScientificQueryGuard(
            shard_count=20,
            default_budget=120,
            max_shards_per_query=20,
        )
        started = time.perf_counter_ns()
        density_response = lake.execute_query(
            {
                "version": "MMRF-SQL-0.8",
                "operation": "interval_density",
                "shard_start": 0,
                "shard_count": 20,
            },
            session_id=f"v10-compat-density:{repeat}",
            guard=guard,
        )
        query_times.append(
            (time.perf_counter_ns() - started) / 1_000_000
        )
    assert density_response is not None
    checks["v08_query_plane_compatible"] = (
        density_response["status"] == "OK"
        and density_response["result"]["prime_count"] == 148_933
        and density_response["scan_profile"]["index_only"]
    )
    timings["v08_density_query"] = {
        "median_ms": statistics.median(query_times),
        "p90_ms": sorted(query_times)[
            int(0.9 * (len(query_times) - 1))
        ],
    }
    lake.close()

# 3. v0.9 governance, migration, provenance and citation compatibility.
migration_validation = verify_migrated_manifest(
    manifest=candidate_manifest,
    project_root=ROOT,
)
provenance_validation = validate_provenance_graph(provenance)
citation_validation = verify_dataset_citation(
    citation,
    manifest=candidate_manifest,
    promotion_receipt=promotion_receipt,
    provenance_graph=provenance,
)
checks["v09_migrated_manifest_compatible"] = migration_validation["valid"]
checks["v09_provenance_compatible"] = provenance_validation["valid"]
checks["v09_citation_compatible"] = citation_validation["valid"]
checks["stable_candidate_binding"] = (
    stable_manifest["source_candidate_manifest_sha256"]
    == candidate_manifest["manifest_sha256"]
)
checks["stable_promotion_binding"] = (
    stable_manifest["governance"]["promotion_receipt_sha256"]
    == promotion_receipt["receipt_sha256"]
)
checks["stable_provenance_binding"] = (
    stable_manifest["provenance_graph_sha256"]
    == provenance["graph_sha256"]
)
checks["stable_citation_binding"] = (
    stable_manifest["citation_sha256"]
    == citation["citation_sha256"]
)

# 4. Upgrade planning.
plan08 = plan_upgrade(v08_manifest)
plan09 = plan_upgrade(candidate_manifest)
plan10 = plan_upgrade(stable_manifest)
checks["v08_requires_migration_and_governance"] = (
    plan08["source_version"] == "0.8"
    and not plan08["eligible_for_direct_freeze"]
)
checks["v09_eligible_with_bindings"] = (
    plan09["source_version"] == "0.9"
    and plan09["eligible_for_direct_freeze"]
)
checks["v10_verify_only"] = (
    plan10["source_version"] == "1.0"
    and plan10["actions"] == ["verify existing stable manifest"]
)

# 5. Release signature and payload verification.
release_manifest_path = (
    ROOT
    / "release_v10"
    / "stable_release_manifest_v1.0.json"
)
release_public_key = (
    ROOT
    / "release_v10"
    / "stable_release_signing.public.pem"
)
release_times = []
release_verification = None
for _ in range(7):
    started = time.perf_counter_ns()
    release_verification = verify_release(
        release_root=ROOT,
        manifest_path=release_manifest_path,
        public_key_path=release_public_key,
        verify_payload=True,
    )
    release_times.append(
        (time.perf_counter_ns() - started) / 1_000_000
    )
assert release_verification is not None and release_verification["valid"]
timings["signed_release_verification"] = {
    "median_ms": statistics.median(release_times),
    "p90_ms": sorted(release_times)[
        int(0.9 * (len(release_times) - 1))
    ],
}
checks["signed_release_valid"] = release_verification["valid"]

# 6. Public installation and verification.
with tempfile.TemporaryDirectory() as td:
    install_target = Path(td) / "public"
    started = time.perf_counter_ns()
    public_state = install_release(
        source_root=ROOT,
        target_root=install_target,
        profile="public-research",
    )
    timings["public_install"] = {
        "elapsed_ms": (
            time.perf_counter_ns() - started
        ) / 1_000_000
    }
    public_verify = verify_installation(install_target)
    checks["public_install_valid"] = public_verify["valid"]
    checks["public_install_profile"] = (
        public_state["profile"] == "public-research"
    )
    checks["public_install_excludes_vault"] = (
        not (install_target / "vault").exists()
    )
    checks["public_install_excludes_network"] = (
        not (install_target / "network").exists()
    )
    checks["public_install_has_stable_data"] = (
        (
            install_target
            / "stable_data"
            / "stable_manifest_v1.0.json"
        ).exists()
    )

    # Installation tamper negative control.
    target_file = install_target / "config" / "public-research.json"
    target_file.write_text(
        target_file.read_text(encoding="utf-8") + "\nTAMPERED\n",
        encoding="utf-8",
    )
    tampered_install = verify_installation(install_target)
    checks["installation_tamper_detected"] = (
        not tampered_install["valid"]
        and bool(tampered_install["mismatches"])
    )

# 7. Controlled profile authorization.
controlled_without_auth = None
with tempfile.TemporaryDirectory() as td:
    try:
        install_release(
            source_root=ROOT,
            target_root=Path(td) / "controlled-no-auth",
            profile="controlled-research",
        )
        controlled_without_auth = "UNEXPECTED_SUCCESS"
    except PermissionError as exc:
        controlled_without_auth = str(exc)
checks["controlled_install_requires_authorization"] = (
    controlled_without_auth != "UNEXPECTED_SUCCESS"
)

with tempfile.TemporaryDirectory() as td:
    temp = Path(td)
    now = datetime.now(timezone.utc)
    authorization = {
        "schema": "mmrf-controlled-install-authorization-1.0",
        "allow_controlled_components": True,
        "approval_reference": "V1-CONFORMANCE-INTERNAL-TEST",
        "approved_profiles": ["controlled-research"],
        "issued_at": (now - timedelta(minutes=1)).isoformat(),
        "expires_at": (now + timedelta(minutes=10)).isoformat(),
    }
    authorization_path = temp / "authorization.json"
    authorization_path.write_text(
        json.dumps(authorization, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    auth_validation = validate_controlled_authorization(
        authorization_path
    )
    checks["controlled_authorization_valid"] = auth_validation["valid"]

    controlled_target = temp / "controlled"
    controlled_state = install_release(
        source_root=ROOT,
        target_root=controlled_target,
        profile="controlled-research",
        controlled_authorization=authorization_path,
    )
    controlled_verify = verify_installation(controlled_target)
    checks["controlled_install_valid"] = controlled_verify["valid"]
    checks["controlled_install_has_vault"] = (
        controlled_target / "vault"
    ).exists()
    checks["controlled_install_has_network"] = (
        controlled_target / "network"
    ).exists()
    checks["controlled_install_records_auth_hash"] = bool(
        controlled_state["controlled_authorization_sha256"]
    )

# Expired controlled authorization.
with tempfile.TemporaryDirectory() as td:
    temp = Path(td)
    now = datetime.now(timezone.utc)
    expired = {
        "schema": "mmrf-controlled-install-authorization-1.0",
        "allow_controlled_components": True,
        "approval_reference": "EXPIRED-TEST",
        "approved_profiles": ["controlled-research"],
        "issued_at": (now - timedelta(days=2)).isoformat(),
        "expires_at": (now - timedelta(days=1)).isoformat(),
    }
    path = temp / "expired.json"
    path.write_text(
        json.dumps(expired, ensure_ascii=False),
        encoding="utf-8",
    )
    checks["expired_controlled_authorization_rejected"] = (
        not validate_controlled_authorization(path)["valid"]
    )

# 8. Stable manifest tamper tests.
tampered_safety = copy.deepcopy(stable_manifest)
tampered_safety["safety"]["source_factor_relations"] = True
checks["stable_safety_tamper_rejected"] = (
    not validate_stable_dataset_manifest(
        tampered_safety,
        project_root=ROOT,
        verify_shards=False,
    )["valid"]
)

tampered_cid_semantics = copy.deepcopy(stable_manifest)
tampered_cid_semantics["cid_semantics"] = "transport-file-sha256"
checks["stable_cid_semantics_tamper_rejected"] = (
    not validate_stable_dataset_manifest(
        tampered_cid_semantics,
        project_root=ROOT,
        verify_shards=False,
    )["valid"]
)

tampered_reviewers = copy.deepcopy(stable_manifest)
tampered_reviewers["governance"]["reviewers"] = [
    "reviewer_math",
    "reviewer_math",
]
checks["duplicate_stable_reviewers_rejected"] = (
    not validate_stable_dataset_manifest(
        tampered_reviewers,
        project_root=ROOT,
        verify_shards=False,
    )["valid"]
)

tampered_manifest_hash = copy.deepcopy(stable_manifest)
tampered_manifest_hash["prime_count"] += 1
checks["stable_manifest_hash_tamper_rejected"] = (
    not validate_stable_dataset_manifest(
        tampered_manifest_hash,
        project_root=ROOT,
        verify_shards=False,
    )["valid"]
)

# Shard tamper in an isolated stable-data copy.
with tempfile.TemporaryDirectory() as td:
    temp_root = Path(td)
    shutil.copytree(
        ROOT / "stable_data",
        temp_root / "stable_data",
    )
    shard_path = (
        temp_root
        / stable_manifest["shards"][7]["file_path"]
    )
    payload = bytearray(shard_path.read_bytes())
    payload[-9] ^= 0x01
    shard_path.write_bytes(payload)
    shard_tamper = validate_stable_dataset_manifest(
        stable_manifest,
        project_root=temp_root,
        verify_shards=True,
    )
    checks["stable_shard_tamper_detected"] = (
        not shard_tamper["valid"]
        and shard_tamper["shards"][7]["reason"]
        == "file_hash_mismatch"
    )

# 9. Release payload tamper.
with tempfile.TemporaryDirectory() as td:
    temp_root = Path(td) / "release"
    temp_root.mkdir(parents=True)
    release_document = json.loads(
        release_manifest_path.read_text(encoding="utf-8")
    )
    # Copy only signed payload paths, manifest and public key.
    for relative in release_document["payload_checksums"]:
        source_path = ROOT / relative
        target_path = temp_root / relative
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
    temp_manifest = (
        temp_root
        / "release_v10"
        / "stable_release_manifest_v1.0.json"
    )
    temp_public = (
        temp_root
        / "release_v10"
        / "stable_release_signing.public.pem"
    )
    temp_manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(release_manifest_path, temp_manifest)
    shutil.copy2(release_public_key, temp_public)

    tamper_relative = "mmrf_stable/__init__.py"
    tamper_path = temp_root / tamper_relative
    tamper_path.write_text(
        tamper_path.read_text(encoding="utf-8") + "\n# tampered\n",
        encoding="utf-8",
    )
    release_tamper = verify_release(
        release_root=temp_root,
        manifest_path=temp_manifest,
        public_key_path=temp_public,
        verify_payload=True,
    )
    checks["release_payload_tamper_detected"] = (
        not release_tamper["valid"]
        and bool(release_tamper["mismatches"])
    )

# 10. Doctor.
doctor_report = doctor(ROOT)
checks["doctor_valid"] = doctor_report["valid"]
checks["doctor_no_private_material"] = (
    not doctor_report["private_material_markers"]
)
checks["doctor_numpy_available"] = doctor_report[
    "dependencies"
]["numpy"]["available"]
checks["doctor_cryptography_available"] = doctor_report[
    "dependencies"
]["cryptography"]["available"]

# 11. Safety endpoints and stable counts.
for field in (
    "source_factor_relations",
    "rsa_target_endpoint",
    "factor_candidate_endpoint",
    "range_narrowing_endpoint",
    "exact_prime_list_endpoint",
    "raw_factor_export",
):
    checks[f"{field}_disabled"] = (
        stable_manifest["safety"][field] is False
    )
checks["stable_prime_count_148933"] = (
    stable_manifest["prime_count"] == 148_933
)
checks["stable_shard_count_20"] = (
    stable_manifest["shard_count"] == 20
)
checks["stable_limit_2000000"] = (
    stable_manifest["limit_exclusive"] == 2_000_000
)

all_passed = all(checks.values())
assert all_passed

results = {
    "version": "1.0.0",
    "release_id": "MMRF-1.0.0",
    "stable_manifest_sha256": stable_manifest["manifest_sha256"],
    "candidate_manifest_sha256": candidate_manifest["manifest_sha256"],
    "promotion_receipt_sha256": promotion_receipt["receipt_sha256"],
    "provenance_graph_sha256": provenance["graph_sha256"],
    "citation_sha256": citation["citation_sha256"],
    "dataset": {
        "limit_exclusive": stable_manifest["limit_exclusive"],
        "prime_count": stable_manifest["prime_count"],
        "shard_count": stable_manifest["shard_count"],
        "columns": stable_manifest["column_order"],
    },
    "timings": timings,
    "upgrade_plans": {
        "0.8": plan08,
        "0.9": plan09,
        "1.0": plan10,
    },
    "stable_validation": stable_validation,
    "release_verification": release_verification,
    "doctor": doctor_report,
    "conformance": {
        "passed": all_passed,
        "check_count": len(checks),
        "checks": checks,
    },
    "boundaries": {
        "public_profile": (
            "Aggregate public mathematics only; no exact-list or "
            "target-conditioned service."
        ),
        "controlled_profile": (
            "Source modules only, authorization-gated, with no private "
            "keys or controlled datasets in the release."
        ),
        "network": (
            "v0.7 provides the real localhost multi-process trial; "
            "v1.0 does not claim geographic federation."
        ),
        "attestation": (
            "Hardware attestation remains an interface boundary, not an "
            "implemented stable guarantee."
        ),
    },
}

(RESULTS / "stable_conformance_results.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

report_rows = "\n".join(
    f"| {name} | {'PASS' if passed else 'FAIL'} |"
    for name, passed in checks.items()
)
timing_rows = "\n".join(
    f"| {name} | "
    f"{values.get('median_ms', values.get('elapsed_ms', 0)):.3f} ms | "
    f"{values.get('p90_ms', values.get('elapsed_ms', 0)):.3f} ms |"
    for name, values in timings.items()
)

report = f"""# MMRF v1.0 Stable Research Infrastructure 實驗報告

## 一、穩定資料身分

```text
Release ID = MMRF-1.0.0
Stable Manifest = {stable_manifest['manifest_sha256']}
Candidate Manifest = {candidate_manifest['manifest_sha256']}
Promotion Receipt = {promotion_receipt['receipt_sha256']}
Provenance Graph = {provenance['graph_sha256']}
Citation = {citation['citation_sha256']}
```

穩定版沒有重新生成 20 個分片，只建立治理與語意封裝。

## 二、資料範圍

```text
Range = [0, {stable_manifest['limit_exclusive']:,})
Prime count = {stable_manifest['prime_count']:,}
Shards = {stable_manifest['shard_count']}
Columns = {len(stable_manifest['column_order'])}
```

## 三、性能

| Operation | Median／Elapsed | P90 |
|---|---:|---:|
{timing_rows}

## 四、版本相容

### v0.8

```json
{json.dumps(plan08, ensure_ascii=False, indent=2)}
```

### v0.9

```json
{json.dumps(plan09, ensure_ascii=False, indent=2)}
```

### v1.0

```json
{json.dumps(plan10, ensure_ascii=False, indent=2)}
```

v0.8 Aggregate Density Query 在隔離複本中仍回傳 148,933，且維持
Index-only 掃描。

## 五、安裝 Profile

### Public

- Stable manifest 與 shards：存在；
- Vault：不存在；
- Network service：不存在；
- Installation inventory：通過。

### Controlled

- 無授權檔：拒絕；
- 有效、短期授權檔：允許；
- 過期授權檔：拒絕；
- 安裝狀態保存授權檔 SHA-256。

## 六、竄改測試

- Stable safety flag 修改：拒絕；
- CID semantics 修改：拒絕；
- Reviewer 重複：拒絕；
- Manifest prime count 修改：拒絕；
- Stable shard 單一位元修改：拒絕；
- Release payload 修改：拒絕；
- Installed config 修改：拒絕。

## 七、Conformance

```text
Checks = {len(checks)}
Passed = {all_passed}
```

| Check | Result |
|---|---|
{report_rows}

## 八、結論

MMRF v1.0 已固定：

```text
Stable Logical CID
→ Promoted Public Dataset
→ Aggregate Query Compatibility
→ Signed Release
→ Verifiable Installation
→ Authorization-gated Controlled Profile
→ Threat Model and Operations Manual
→ Release Freeze
```
"""
(RESULTS / "MMRF_v1.0_Stable_Research_Infrastructure實驗報告.md").write_text(
    report,
    encoding="utf-8",
)

print(json.dumps(results, ensure_ascii=False, indent=2))
