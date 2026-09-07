# MMRF Prime Expansion Handoff — 2026-09-06

Status: `CANDIDATE_UNPROMOTED`

Catch-up provenance: `2026-09-06` is the logical relay date. This artifact was physically generated during the catch-up run on `2026-09-07`; it does not claim to have physically existed on the logical date.

## Completed unit

- Range: `[5,500,000, 5,600,000)`
- Base generation: `2`
- Candidate generation: `38`
- New primes: `6,402`
- Shard index: `55`
- Logical CID: `mmrf-shard:8febac14d2b8b2653400d8856af5ffffc931e277aa5be228459b836c645051cf`
- Candidate manifest SHA-256: `251e8c38df188f073dfa0747267181159ae600318088166c2ea1bf0d95917acf`

- Prior candidate manifest SHA-256: `f9bb26a9cee02638b633300a4e0a3f67746c6b1f650dad493c519072d0956387`

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
