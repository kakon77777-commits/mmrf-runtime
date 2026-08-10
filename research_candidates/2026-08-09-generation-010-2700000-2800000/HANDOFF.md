# MMRF Prime Expansion Handoff — 2026-08-09

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[2,700,000, 2,800,000)`
- Base generation: `2`
- Candidate generation: `10`
- New primes: `6,717`
- Shard index: `27`
- Logical CID: `mmrf-shard:fb8f159a44f14e8a643e585a6088dd972aad109b4052065bb8a03fb8b849ff50`
- Candidate manifest SHA-256: `68cc26d580b299c65d05732911f3abdc3ed653a1de44971bbdfb6b3b933be5bd`

- Prior candidate manifest SHA-256: `b4a88ceb4d2bd619947d7d6bad34aabd6c9e7a2ff0d3befecc8be58599dbe005`

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
