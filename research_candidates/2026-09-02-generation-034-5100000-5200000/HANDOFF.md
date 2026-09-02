# MMRF Prime Expansion Handoff — 2026-09-02

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[5,100,000, 5,200,000)`
- Base generation: `2`
- Candidate generation: `34`
- New primes: `6,436`
- Shard index: `51`
- Logical CID: `mmrf-shard:7da6f55e5d65e976b315ddfb02fd9c076a791c91e0fc01e4ea81a2186c404649`
- Candidate manifest SHA-256: `acacc64815ba3ed178a2f21e86c30ddb61cc7d42f63d7d84c46c016fac336180`

- Prior candidate manifest SHA-256: `a6fd5be47c54bfb45216e0eba286f893940c4d41e2196689f8473a476b2cccda`

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
