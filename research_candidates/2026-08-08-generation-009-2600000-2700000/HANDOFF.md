# MMRF Prime Expansion Handoff — 2026-08-08

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[2,600,000, 2,700,000)`
- Base generation: `2`
- Candidate generation: `9`
- New primes: `6,765`
- Shard index: `26`
- Logical CID: `mmrf-shard:f30bc2dae02a1dd1d96b4914274f0cf453e217df0eec7da00cc949eae67b5964`
- Candidate manifest SHA-256: `b4a88ceb4d2bd619947d7d6bad34aabd6c9e7a2ff0d3befecc8be58599dbe005`

- Prior candidate manifest SHA-256: `93a2af608e1c09116019db241b183442beab76cd44ff55353551eb93932b2b87`

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
