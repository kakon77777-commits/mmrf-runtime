# MMRF Prime Expansion Handoff — 2026-08-10

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[2,800,000, 2,900,000)`
- Base generation: `2`
- Candidate generation: `11`
- New primes: `6,747`
- Shard index: `28`
- Logical CID: `mmrf-shard:f6c64316193d7c6aedfaf30fd317e66e3c1d536060793b969d9937dfa147a811`
- Candidate manifest SHA-256: `1cd497c22782079c02acefc07bca3c7f850f3fa26bb5dc52c82101cea6dbf532`

- Prior candidate manifest SHA-256: `68cc26d580b299c65d05732911f3abdc3ed653a1de44971bbdfb6b3b933be5bd`

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
