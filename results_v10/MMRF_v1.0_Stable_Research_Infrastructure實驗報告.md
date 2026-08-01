# MMRF v1.0 Stable Research Infrastructure 實驗報告

## 一、穩定資料身分

```text
Release ID = MMRF-1.0.0
Stable Manifest = a5caea22a57efaac915c00dd92c655b1126e0b6d9b2b93790e48bc167733e0d1
Candidate Manifest = 73015c5329ae71900ef3f4aca7f35152f3d96a435e65e3bddbd1ae513d597420
Promotion Receipt = 6ad7c85305f45cef095f72eb55ae9f097d9a70388615e5f609fbb83f024c0658
Provenance Graph = ffb6dd8d5f7e5e54a559d38a09e1262933e5898f7151627174836624448fd238
Citation = c8b87bbc7a1dde104a202d613c275650be7caa482e9f3d6ad3ca93a3f3e83146
```

穩定版沒有重新生成 20 個分片，只建立治理與語意封裝。

## 二、資料範圍

```text
Range = [0, 2,000,000)
Prime count = 148,933
Shards = 20
Columns = 10
```

## 三、性能

| Operation | Median／Elapsed | P90 |
|---|---:|---:|
| stable_manifest_and_20_shards | 1.012 ms | 1.094 ms |
| v08_density_query | 1.320 ms | 2.370 ms |
| signed_release_verification | 3.310 ms | 3.514 ms |
| public_install | 7.222 ms | 7.222 ms |

## 四、版本相容

### v0.8

```json
{
  "source_version": "0.8",
  "eligible_for_direct_freeze": false,
  "actions": [
    "run MMRF-SCHEMA-0.8-TO-0.9 migration",
    "verify all migrated logical CIDs",
    "submit signed dataset proposal",
    "obtain at least two distinct approvals",
    "publish promotion receipt, provenance graph and citation",
    "freeze stable manifest 1.0"
  ]
}
```

### v0.9

```json
{
  "source_version": "0.9",
  "eligible_for_direct_freeze": true,
  "actions": [
    "verify promotion receipt",
    "verify provenance DAG",
    "verify citation bindings",
    "freeze stable manifest 1.0 without rewriting shards"
  ]
}
```

### v1.0

```json
{
  "source_version": "1.0",
  "eligible_for_direct_freeze": false,
  "actions": [
    "verify existing stable manifest"
  ]
}
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
Checks = 47
Passed = True
```

| Check | Result |
|---|---|
| stable_manifest_valid | PASS |
| all_20_stable_shards_valid | PASS |
| stable_frozen_semantics_exact | PASS |
| v08_query_plane_compatible | PASS |
| v09_migrated_manifest_compatible | PASS |
| v09_provenance_compatible | PASS |
| v09_citation_compatible | PASS |
| stable_candidate_binding | PASS |
| stable_promotion_binding | PASS |
| stable_provenance_binding | PASS |
| stable_citation_binding | PASS |
| v08_requires_migration_and_governance | PASS |
| v09_eligible_with_bindings | PASS |
| v10_verify_only | PASS |
| signed_release_valid | PASS |
| public_install_valid | PASS |
| public_install_profile | PASS |
| public_install_excludes_vault | PASS |
| public_install_excludes_network | PASS |
| public_install_has_stable_data | PASS |
| installation_tamper_detected | PASS |
| controlled_install_requires_authorization | PASS |
| controlled_authorization_valid | PASS |
| controlled_install_valid | PASS |
| controlled_install_has_vault | PASS |
| controlled_install_has_network | PASS |
| controlled_install_records_auth_hash | PASS |
| expired_controlled_authorization_rejected | PASS |
| stable_safety_tamper_rejected | PASS |
| stable_cid_semantics_tamper_rejected | PASS |
| duplicate_stable_reviewers_rejected | PASS |
| stable_manifest_hash_tamper_rejected | PASS |
| stable_shard_tamper_detected | PASS |
| release_payload_tamper_detected | PASS |
| doctor_valid | PASS |
| doctor_no_private_material | PASS |
| doctor_numpy_available | PASS |
| doctor_cryptography_available | PASS |
| source_factor_relations_disabled | PASS |
| rsa_target_endpoint_disabled | PASS |
| factor_candidate_endpoint_disabled | PASS |
| range_narrowing_endpoint_disabled | PASS |
| exact_prime_list_endpoint_disabled | PASS |
| raw_factor_export_disabled | PASS |
| stable_prime_count_148933 | PASS |
| stable_shard_count_20 | PASS |
| stable_limit_2000000 | PASS |

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
