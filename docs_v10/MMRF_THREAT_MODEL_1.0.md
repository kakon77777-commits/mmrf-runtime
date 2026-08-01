# MMRF v1.0 Threat Model

## 1. Protected assets

| Asset | Primary requirement |
|---|---|
| Stable public shards and CIDs | Integrity and availability |
| Manifest, proposal and promotion chain | Integrity and provenance |
| L2/L3 relationship data | Confidentiality and controlled use |
| Reviewer and authority signing keys | Confidentiality and non-repudiation |
| Query and governance audit chains | Append-only integrity |
| Node catalog state | Freshness, consistency and anti-equivocation |
| Recovery material | Threshold confidentiality |

## 2. Adversaries

MMRF assumes possible:

- unauthenticated external clients;
- registered researchers attempting query-shape abuse;
- compromised replica nodes;
- a malicious or careless reviewer;
- a compromised transparency-log operator;
- package or mirror tampering;
- rollback, replay and same-version split views;
- leakage of old encrypted envelopes;
- unauthorized attempts to enable controlled components.

## 3. Trust boundaries

```text
Public Query Plane
    ↓ aggregate-only contract
Public L0 Data Lake
    ↓ signed proposal and independent review
Governance Plane
    ↓ explicit authorization only
Controlled L2 Enclave / L3 Vault
```

Crossing a lower boundary does not imply authorization for a higher boundary.

## 4. Principal threats and controls

| Threat | Stable control |
|---|---|
| Modified release payload | Signed release manifest and file checksums |
| Modified installation | Installation inventory and state hash |
| Shard corruption | File SHA-256, logical content CID and sampling |
| Catalog rollback | Per-node monotonic version and previous hash |
| Catalog split view | Same-node same-version conflict rejection |
| Under-replication | Explicit replication-factor calculation and repair |
| Unsafe dataset promotion | Safety gate before reviewer counting |
| Reviewer duplication | Unique reviewer constraint |
| Proposal or review tampering | Ed25519 signatures |
| Provenance rewrite | Graph hash and DAG requirement |
| Citation substitution | Manifest, receipt and graph hash binding |
| Target-conditioned public query | Fixed aggregate-only query schema |
| Controlled-profile activation | Time-bounded authorization file |
| Key leakage in release | Filename and PEM-content release scan |
| Log rollback/equivocation | Witness state and gossip |
| Revoked node using valid TLS cert | Signed policy snapshot checked after mTLS |

## 5. Residual risks

- Software-only authorization files are not HSM approvals.
- Local Ed25519 test identities are not organizational identities.
- The release cannot erase data already copied by a revoked node.
- Public shard files contain public prime values, although no exact-list service
  is exposed.
- Localhost federation tests do not prove cross-region resilience.
- Hardware attestation adapters remain unimplemented.
- Recovery ceremonies still require organizational controls.

## 6. Explicitly forbidden use

The stable public infrastructure must not be extended through a patch release
to accept third-party RSA moduli, return factor candidates, reconstruct source–
factor relationships or provide repeated target-conditioned range reduction.
Such a change requires a major-version security review and is outside v1.0.
