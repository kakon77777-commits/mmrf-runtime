# MMRF Prime Expansion Handoff — 2026-09-01

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[5,000,000, 5,100,000)`
- Base generation: `2`
- Candidate generation: `33`
- New primes: `6,458`
- Shard index: `50`
- Logical CID: `mmrf-shard:36ac929c7395901fcea02413953b17e7216a45cc86a387d3a85e930f0666e610`
- Candidate manifest SHA-256: `a6fd5be47c54bfb45216e0eba286f893940c4d41e2196689f8473a476b2cccda`

- Prior candidate manifest SHA-256: `74b07f88d6440c4457c65ff330d793024aa8d5f28617d0ac2f781cdfcda8369f`

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
