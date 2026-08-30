# MMRF Prime Expansion Handoff — 2026-08-30

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[4,800,000, 4,900,000)`
- Base generation: `2`
- Candidate generation: `31`
- New primes: `6,553`
- Shard index: `48`
- Logical CID: `mmrf-shard:6cb0afc7e7d528b229c2e37811b5515657888191f53735dba1193b1927117f13`
- Candidate manifest SHA-256: `a22cda9aec7aac3d1e597816078fb39eed7164c74e30071f9b81264927297f03`

- Prior candidate manifest SHA-256: `c29c231466b66d862a026d0dbed01a2d892ce96fdff48a0af5653eff77a34d18`

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
