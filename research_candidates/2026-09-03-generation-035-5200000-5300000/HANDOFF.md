# MMRF Prime Expansion Handoff — 2026-09-03

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[5,200,000, 5,300,000)`
- Base generation: `2`
- Candidate generation: `35`
- New primes: `6,493`
- Shard index: `52`
- Logical CID: `mmrf-shard:f0b61eae0735f30259cf7272025a9b7a4acd0ad6d3ee4c3d8ff7896fdcc2c3b9`
- Candidate manifest SHA-256: `eb7f70fb4773208c8c2bb5988295bcfa62ff3540b9b4c6444e43f87d371b8f96`

- Prior candidate manifest SHA-256: `acacc64815ba3ed178a2f21e86c30ddb61cc7d42f63d7d84c46c016fac336180`

## Verification

- range_ok: `True`
- strictly_increasing: `True`
- unique: `True`
- numpy_sieve_match: `True`
- independent_segmented_sieve_match: `True`
- ordinal_continuity: `True`
- residue_6_valid: `True`
- residue_30_valid: `True`
- residue_210_valid: `True`
- wheel30_valid: `True`

## Next relay

1. Re-run this workflow independently and compare the logical CID.
2. Inspect the candidate shard and candidate manifest without changing the frozen v1.0 data.
3. Add an independent math/data review before any promotion proposal.
4. Do not publish this candidate as a stable generation until the governance chain is complete.
