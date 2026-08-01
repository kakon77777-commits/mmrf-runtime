# MMRF Compatibility Matrix — v0.9 RC

| Component | Input | Output | Compatibility |
|---|---|---|---|
| Public Lake | Manifest 0.8 | Manifest 0.8 | Preserved |
| Migration | Shards 0.8 | Shards 0.9 | Explicit profile required |
| Query Plane | MMRF-SQL 0.8 | Aggregate responses 0.8 | Preserved |
| Catalog | Manifest 0.8 or 0.9 hash | Catalog 0.9 | Supported |
| Governance | Candidate Manifest 0.9 | Promotion Receipt 0.9 | Required for v0.9 promotion |
| Provenance | v0.8/v0.9 hashes | Graph 0.9 | Supported |
| Citation | Promoted Manifest 0.9 | Citation 0.9 | Supported |
| L2/L3 Vault | Controlled objects | No public promotion | Intentionally isolated |

The v0.8 public dataset remains readable. Migration creates a new branch and
does not overwrite v0.8 shards.
