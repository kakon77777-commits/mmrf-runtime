# MMRF v0.9 Scientific Federation & Dataset Governance

## Federation catalog

Every storage node publishes a signed, monotonic catalog announcement. A
catalog entry binds:

- node identity;
- catalog version;
- previous announcement hash;
- dataset manifest hash;
- shard CID;
- transport-file SHA-256;
- logical-content SHA-256;
- row count.

Federation coverage is not inferred from filenames. A replica is counted only
when all hashes agree with the promoted manifest.

## Replication policy

The v0.9 experiment requires three replicas for every public shard. A partial
Node C announcement produces an explicit repair set. Promotion and replication
remain separate:

```text
Replication proves availability.
Promotion proves governance approval.
```

A fully replicated candidate is not automatically a published dataset.

## Schema migration

Profile `MMRF-SCHEMA-0.8-TO-0.9` adds `wheel30_class`, a deterministic public
derivative of `residue_30`.

Each migrated shard records:

```text
source_cid
target_cid
source_file_sha256
target_file_sha256
migration_profile
```

Logical CIDs are reproducible across migration replays. NPZ container hashes
may differ because the compressed ZIP transport container is not the logical
content identity.

## Governance state machine

```text
SIGNED_PROPOSAL
→ UNDER_REVIEW
→ APPROVED_BY_2_OF_3
→ PROMOTED
```

A rejection blocks promotion. The same reviewer cannot count twice.

The safety gate executes before review counting and requires every candidate to
remain `L0_PUBLIC_MATH`.

## Provenance

The provenance graph is a hash-bound DAG linking:

- source manifest;
- schema migration;
- candidate manifest;
- proposal;
- independent reviews;
- promotion receipt;
- prior workflow output.

Cycles invalidate the graph.

## Citation

A stable citation binds the promoted manifest, promotion receipt and provenance
graph. The citation identifier is derived from the promoted manifest hash.

## Stable-version boundary

v0.9 is a release-candidate governance prototype. Production deployment still
needs:

- organizational identities;
- HSM-backed signing;
- independent reviewer administration;
- remote catalog transport;
- durable object-store APIs;
- catalog garbage collection;
- citation registry publication;
- legal data-retention policy.
