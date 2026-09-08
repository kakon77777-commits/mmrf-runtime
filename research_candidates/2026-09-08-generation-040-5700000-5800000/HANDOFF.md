# MMRF Prime Expansion Handoff — 2026-09-08

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[5,700,000, 5,800,000)`
- Base generation: `2`
- Candidate generation: `40`
- New primes: `6,387`
- Shard index: `57`
- Logical CID: `mmrf-shard:86679f8917735b4fadf511b34375623056943190d97321eb3ed0c71e7d61a2dc`
- Candidate manifest SHA-256: `3dea65d86808923707db1cc73dc6ad703364bd94a9408c8561562ba51503ee3d`

- Prior candidate manifest SHA-256: `a200e3a8739f00e10a74f093893e36aa7b384733da71f7f6ca6577e843d984e8`

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
