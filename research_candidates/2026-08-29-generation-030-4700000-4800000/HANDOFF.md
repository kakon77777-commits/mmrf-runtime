# MMRF Prime Expansion Handoff — 2026-08-29

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[4,700,000, 4,800,000)`
- Base generation: `2`
- Candidate generation: `30`
- New primes: `6,475`
- Shard index: `47`
- Logical CID: `mmrf-shard:61cde32e3d6249a9cf647964bc01667913339f4163d805c1aa034a2b14d5555d`
- Candidate manifest SHA-256: `c29c231466b66d862a026d0dbed01a2d892ce96fdff48a0af5653eff77a34d18`

- Prior candidate manifest SHA-256: `73202525d48470b405943930fb050147e8658bedc10f069b77b141de22df5fed`

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
