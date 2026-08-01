# MMRF v1.0 Compatibility and Upgrade Matrix

| Source | Read | Query | Direct stable freeze | Required path |
|---|---:|---:|---:|---|
| v0.1 charter/safety schemas | Yes | No | No | Historical policy dependency |
| v0.4 Enclave | Yes | Controlled only | No | Explicit controlled profile |
| v0.5 Vault | Yes | Controlled only | No | Explicit controlled profile |
| v0.6 Transparency/Recovery | Yes | Governance support | No | Explicit controlled profile |
| v0.7 mTLS Policy Network | Yes | Governance support | No | Separate service deployment |
| v0.8 Data Lake Manifest | Yes | MMRF-SQL 0.8 | No | Migrate → review → promote |
| v0.9 Candidate Manifest | Yes | MMRF-SQL 0.8 | Yes, with bindings | Verify receipt, graph and citation |
| v1.0 Stable Manifest | Yes | MMRF-SQL 0.8 | Already stable | Verify only |

## Upgrade plans

### 0.8

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

### 0.9

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

### 1.0

```json
{
  "source_version": "1.0",
  "eligible_for_direct_freeze": false,
  "actions": [
    "verify existing stable manifest"
  ]
}
```
