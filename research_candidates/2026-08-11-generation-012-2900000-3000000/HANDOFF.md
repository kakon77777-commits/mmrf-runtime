# MMRF Prime Expansion Handoff — 2026-08-11

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[2,900,000, 3,000,000)`
- Base generation: `2`
- Candidate generation: `12`
- New primes: `6,707`
- Shard index: `29`
- Logical CID: `mmrf-shard:35ece3d78825fca5a67ccfd5e719b5c89421da31f7161d232ecffbadf82452f1`
- Candidate manifest SHA-256: `a1ee18026b7a646ea9da0633deaf11c091ba0a11306c84d02557d643aaf413c8`

- Prior candidate manifest SHA-256: `1cd497c22782079c02acefc07bca3c7f850f3fa26bb5dc52c82101cea6dbf532`

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
