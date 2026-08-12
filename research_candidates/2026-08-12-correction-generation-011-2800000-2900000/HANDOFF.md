# MMRF Prime Expansion Handoff — 2026-08-12

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[2,800,000, 2,900,000)`
- Base generation: `2`
- Candidate generation: `11`
- New primes: `6,747`
- Shard index: `28`
- Logical CID: `mmrf-shard:3e96b42b7d4775ea9563f4e6ed60cecb4d479a4a61332979ba0c78e81f4b7e3d`
- Candidate manifest SHA-256: `570fa314533359ed17b7186472a7c981d0f1da507c4178a9c9595f7c002190c8`

- Prior candidate manifest SHA-256: `57f026da358fc38164e4a905d81622003b46a18b4d4bd342bc440c003393e3a4`

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
