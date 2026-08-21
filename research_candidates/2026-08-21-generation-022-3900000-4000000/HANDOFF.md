# MMRF Prime Expansion Handoff — 2026-08-21

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[3,900,000, 4,000,000)`
- Base generation: `2`
- Candidate generation: `22`
- New primes: `6,535`
- Shard index: `39`
- Logical CID: `mmrf-shard:7af2ce50986e9ddd8ea945471fa1147ab478afae771036000c760ee188f0362d`
- Candidate manifest SHA-256: `f346e629e66e37988b42001f044c5430dfadf934fe4a9df1dd63f88c8efdc49b`

- Prior candidate manifest SHA-256: `29b080f8cd14a77b67ed0c714b1319adecf51d18c4ab40c1677a3a827b6cde3f`

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
