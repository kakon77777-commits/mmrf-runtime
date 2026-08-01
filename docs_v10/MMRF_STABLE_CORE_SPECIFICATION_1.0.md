# MMRF v1.0 Stable Core Specification

## 1. Release identity

```text
Release ID: MMRF-1.0.0
Status: STABLE
Public profile: MMRF-PUBLIC-RESEARCH-1.0
Stable dataset manifest:
a5caea22a57efaac915c00dd92c655b1126e0b6d9b2b93790e48bc167733e0d1
```

MMRF v1.0 freezes the semantics established by the v0.9 promoted dataset. It
does not rewrite the 20 promoted shards and does not create a new logical
prime-data representation.

## 2. Stable public data

```text
Range: [0, 2,000,000)
Prime count: 148,933
Shards: 20
Logical source schema: 0.9
Stable schema wrapper: 1.0
```

The stable wrapper binds:

- v0.8 source manifest;
- v0.9 migrated candidate manifest;
- promotion receipt;
- provenance graph;
- persistent citation;
- frozen safety and CID semantics.

## 3. Frozen semantics

```json
{
  "logical_cid": "CID is the SHA-256 identity of canonical logical column content, not the transport container.",
  "public_classification": "Only L0_PUBLIC_MATH data can enter the public stable dataset.",
  "query_surface": "Public queries are aggregate-only and may not accept target integers, RSA moduli, factors, candidates or narrowing requests.",
  "governance_precedence": "Safety validation runs before review counting or promotion.",
  "review_uniqueness": "Promotion requires at least two distinct approved reviewer identities; duplicate reviewers do not increase quorum.",
  "provenance": "Promoted datasets require a hash-bound acyclic provenance graph.",
  "citation": "Stable citations bind the dataset manifest, promotion receipt and provenance graph.",
  "controlled_default": "Controlled Vault, Enclave and network components are disabled in the default public installation profile."
}
```

These semantics require a major-version change if altered.

## 4. Public query surface

The stable public query language remains `MMRF-SQL-0.8`:

- dataset metadata;
- interval density;
- gap quantiles;
- gap histogram;
- residue distribution;
- family counts;
- workflow replay.

The stable release intentionally does not add:

- exact-prime-list service;
- nearest-prime-to-target service;
- externally supplied integer targets;
- RSA modulus analysis;
- factor candidates;
- range narrowing;
- source-factor relationships.

## 5. Profiles

### public-research

Default installation. Includes:

- stable dataset;
- aggregate query plane;
- federation and governance verification;
- schemas and operational documentation;
- public workflow and citation.

### controlled-research

Optional installation. Adds source modules for:

- Controlled Enclave;
- Federated Vault;
- Transparency and Recovery Plane;
- Policy Authority and mTLS network trial.

It requires an explicit, time-bounded authorization file. No private key or
controlled dataset is distributed with the stable release.

## 6. Compatibility

- Manifest 0.8 remains readable and requires migration plus governance before
  stable promotion.
- Manifest 0.9 can be frozen directly only when promotion, provenance and
  citation bindings verify.
- Manifest 1.0 is verified without rewriting shards.
- Existing MMRF-SQL 0.8 aggregate queries remain compatible.

## 7. Stable non-claims

MMRF v1.0 is not:

- an RSA-breaking service;
- a target-conditioned factor oracle;
- hardware-backed attestation;
- a production HSM deployment;
- a geographically independent federation;
- a guarantee that revocation erases previously copied data.
