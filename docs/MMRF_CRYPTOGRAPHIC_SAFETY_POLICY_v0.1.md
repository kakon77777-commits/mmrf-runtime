# MMRF Cryptographic Safety Policy v0.1

## 1. Purpose restriction

MMRF supports mathematics, computation, physics and defensive cryptography.
It does not support unauthorized recovery of private keys or factoring of
third-party RSA moduli.

## 2. Default deny for target-conditioned cryptanalysis

The following request types are denied by default:

- arbitrary external modulus → factor candidate query;
- public key → factor neighborhood query;
- repeated range narrowing around one target;
- bulk target uploads;
- export of sensitive relation indexes;
- reconstruction of a hidden candidate set through query composition.

## 3. Authorized cryptography research

Allowed environments include:

- toy keys;
- intentionally weak keys;
- published research challenges;
- keys owned by the researcher;
- defensive weak-key detection;
- key-generation auditing;
- post-quantum migration research.

Authorization must be documented and purpose-bound.

## 4. Full-access control

Full access requires:

- data-owner approval;
- independent security approval;
- a declared dataset;
- a declared computation;
- time-limited credentials;
- immutable audit;
- export review.

## 5. Safe output transformation

Sensitive queries should return, when possible:

- aggregate statistics;
- confidence intervals;
- categorical findings;
- non-invertible sketches;
- approved certificates;
- redacted reproducibility bundles.

They should not return raw candidate lists or target-specific narrowing paths.

## 6. Abuse monitoring

Risk indicators include:

- many queries against the same modulus;
- correlated accounts;
- narrow bit-range enumeration;
- repeated residue filtering;
- attempts to reconstruct hidden records;
- unexplained bulk export;
- mismatch between declared and actual workload.

## 7. Emergency controls

MMRF must support:

- immediate account suspension;
- query-token revocation;
- dataset sealing;
- audit preservation;
- export invalidation where technically possible;
- security review before reopening.

## 8. Research publication review

Before publishing a result, reviewers must ask:

1. Does the result improve mathematical knowledge?
2. Does it expose target-conditioned factor narrowing?
3. Can the public artifact be recombined into a practical attack?
4. Can aggregation or delayed release preserve the research value?
5. Is a defensive mitigation available before release?
