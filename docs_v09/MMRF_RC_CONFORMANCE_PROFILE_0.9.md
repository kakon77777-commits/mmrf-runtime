# MMRF v0.9 RC Conformance Profile

## Result

```text
Profile: MMRF-RC-CONFORMANCE-0.9
Checks: 26
Passed: True
```

## Mandatory groups

### Federation

- Signed catalog announcements.
- Monotonic per-node catalog versions.
- Previous-announcement hash continuity.
- Same-version split-catalog rejection.
- Hash-conflict detection.
- Minimum replication enforcement.
- Repair convergence.

### Migration

- Source-manifest binding.
- Source-CID to target-CID lineage.
- All target shards verify.
- Logical migration replay produces identical target content CIDs.
- Safety metadata remains L0-only.

### Governance

- Signed proposer identity.
- Signed independent reviewer identities.
- Two distinct approvals required.
- A rejection blocks promotion.
- Duplicate reviewer does not increase quorum.
- Safety gate runs before promotion.
- Promotion receipt binds proposal and candidate manifest.

### Provenance and citation

- Provenance graph hash verifies.
- Graph is acyclic.
- Citation binds manifest, promotion receipt and provenance graph.
- Modified citation fields invalidate the citation.

### Safety

The following fields must remain false:

```text
source_factor_relations
rsa_target_endpoint
factor_candidate_endpoint
range_narrowing_endpoint
exact_prime_list_endpoint
raw_factor_export
```

## RC freeze guidance

A v1.0 release must not change these semantics without a new major profile:

1. logical CID meaning;
2. catalog monotonicity;
3. safety-gate precedence;
4. independent-review uniqueness;
5. promotion-receipt binding;
6. provenance DAG requirement;
7. citation hash binding.
