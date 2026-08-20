# MMRF Prime Expansion Handoff — 2026-08-20

Status: `CANDIDATE_UNPROMOTED`

Catch-up execution note: this artifact was generated on 2026-08-20 as part of the batch that restored the paused daily relay. The 2026-08-20 heading and `created_on` / `as-of` values are logical relay identifiers; no earlier physical creation is implied.

## Completed unit

- Range: `[3,800,000, 3,900,000)`
- Base generation: `2`
- Candidate generation: `21`
- New primes: `6,624`
- Shard index: `38`
- Logical CID: `mmrf-shard:cae4da26bd05bb4e3269eb9a137d78b0d13189ac5e585bd8ea49ebd7d5756c2a`
- Candidate manifest SHA-256: `29b080f8cd14a77b67ed0c714b1319adecf51d18c4ab40c1677a3a827b6cde3f`

- Prior candidate manifest SHA-256: `e8ec45d6d938b6b3da6cf8d508685e2a40695e787982b70570b6aa0f8512370e`

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
