# MMRF Prime Expansion Handoff — 2026-08-12

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[2,300,000, 2,400,000)`
- Base generation: `2`
- Candidate generation: `6`
- New primes: `6,791`
- Shard index: `23`
- Logical CID: `mmrf-shard:2b938348e5ed8454e0d6d1b7bb77e124b851b60a51bc5d89b32668f4621d73ae`
- Candidate manifest SHA-256: `5a1f705e8f6ecb9bffbdfae7b19d504088f5f0c71ccdc3a0a7af5055034f30c3`

- Prior candidate manifest SHA-256: `a23e9dd97d2cbd064c41acf775bac8527f8eb61a5575f11f721f652485c53ba8`

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
