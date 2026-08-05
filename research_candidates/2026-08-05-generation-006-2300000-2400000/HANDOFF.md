# MMRF Prime Expansion Handoff — 2026-08-05

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[2,300,000, 2,400,000)`
- Base generation: `2`
- Candidate generation: `6`
- New primes: `6,791`
- Shard index: `23`
- Logical CID: `mmrf-shard:2cfcf25da41975f148b33dbfdef52f1592ddcffd6b9dc36e0e97082a666b658f`
- Candidate manifest SHA-256: `81cc8ce7cdfa40bac836a9e279204192e8bf5e6f15cea7b6a9a12dd82b8ecb14`

- Prior candidate manifest SHA-256: `9ab2b083590dcaac0bdfa65ca8c1c22bea758223b3e4479c16288055ab771847`

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
