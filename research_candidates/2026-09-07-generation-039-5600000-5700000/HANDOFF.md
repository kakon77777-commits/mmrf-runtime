# MMRF Prime Expansion Handoff — 2026-09-07

Status: `CANDIDATE_UNPROMOTED`

Catch-up provenance: `2026-09-07` is both the logical relay date and the physical execution date for this artifact.

## Completed unit

- Range: `[5,600,000, 5,700,000)`
- Base generation: `2`
- Candidate generation: `39`
- New primes: `6,404`
- Shard index: `56`
- Logical CID: `mmrf-shard:4731bfa9cdadfd34b426fbec035cc9ea681f2ac3e57026fd71108a8c2a6883bf`
- Candidate manifest SHA-256: `a200e3a8739f00e10a74f093893e36aa7b384733da71f7f6ca6577e843d984e8`

- Prior candidate manifest SHA-256: `251e8c38df188f073dfa0747267181159ae600318088166c2ea1bf0d95917acf`

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
