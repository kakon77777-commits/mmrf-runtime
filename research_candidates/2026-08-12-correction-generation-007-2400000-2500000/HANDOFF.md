# MMRF Prime Expansion Handoff — 2026-08-12

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[2,400,000, 2,500,000)`
- Base generation: `2`
- Candidate generation: `7`
- New primes: `6,770`
- Shard index: `24`
- Logical CID: `mmrf-shard:eb9df7c9d70062bb9a0cb525be9c5f5ef639b39d85f4ec60335e92374afa3085`
- Candidate manifest SHA-256: `029a3134f17b92b508599bcc044de9795aa91827f2385667c1ff0a06e07cb542`

- Prior candidate manifest SHA-256: `5a1f705e8f6ecb9bffbdfae7b19d504088f5f0c71ccdc3a0a7af5055034f30c3`

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
