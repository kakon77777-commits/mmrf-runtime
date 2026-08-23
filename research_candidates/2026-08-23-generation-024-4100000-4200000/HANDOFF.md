# MMRF Prime Expansion Handoff — 2026-08-23

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[4,100,000, 4,200,000)`
- Base generation: `2`
- Candidate generation: `24`
- New primes: `6,540`
- Shard index: `41`
- Logical CID: `mmrf-shard:2f10499c7ab8d6e322329c88a7eea00f9abcb36a4c4069529c67f7964a9e9116`
- Candidate manifest SHA-256: `8d0ea8c9f54a05a385e4880f57e86e56c23f25ab5464ceeb0063ba3f61333d26`

- Prior candidate manifest SHA-256: `83e83b3de6da2a2fa6a8e29a60958685645373def0a4aee5b3ef7467fc97a546`

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
