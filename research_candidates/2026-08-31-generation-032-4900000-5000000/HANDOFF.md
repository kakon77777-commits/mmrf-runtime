# MMRF Prime Expansion Handoff — 2026-08-31

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[4,900,000, 5,000,000)`
- Base generation: `2`
- Candidate generation: `32`
- New primes: `6,521`
- Shard index: `49`
- Logical CID: `mmrf-shard:69d8f924701b0a604ec4ca4690862f230236cc7fc602d2240152a416f6060ac3`
- Candidate manifest SHA-256: `74b07f88d6440c4457c65ff330d793024aa8d5f28617d0ac2f781cdfcda8369f`

- Prior candidate manifest SHA-256: `a22cda9aec7aac3d1e597816078fb39eed7164c74e30071f9b81264927297f03`

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
