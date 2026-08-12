# MMRF Prime Expansion Handoff — 2026-08-12

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[2,900,000, 3,000,000)`
- Base generation: `2`
- Candidate generation: `12`
- New primes: `6,707`
- Shard index: `29`
- Logical CID: `mmrf-shard:2787fad3ee1947d351399bb1641771f981ee15409e3fcb6597f89ad6c7b13d1c`
- Candidate manifest SHA-256: `df5047cb43539644312ada6f20407c73b93a1064135de23d9298a24651aeef46`

- Prior candidate manifest SHA-256: `570fa314533359ed17b7186472a7c981d0f1da507c4178a9c9595f7c002190c8`

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
