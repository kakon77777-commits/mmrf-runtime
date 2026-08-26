# MMRF Prime Expansion Handoff — 2026-08-26

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[4,400,000, 4,500,000)`
- Base generation: `2`
- Candidate generation: `27`
- New primes: `6,613`
- Shard index: `44`
- Logical CID: `mmrf-shard:e4bc914637524dd21fee95b2bc12fc4dd260f5648a40aa191c7bcbbeb0592f4d`
- Candidate manifest SHA-256: `f2cd9f7047da23fd5788acc3a5dd41a833cbd07cc86df504cc264021843b70fa`

- Prior candidate manifest SHA-256: `f069e7cd2ffd8ce928a4966d31fe35d610e71fe7a535ad5f3e5d1aee178bcc56`

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
