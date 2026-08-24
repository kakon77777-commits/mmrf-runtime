# MMRF Prime Expansion Handoff — 2026-08-24

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[4,200,000, 4,300,000)`
- Base generation: `2`
- Candidate generation: `25`
- New primes: `6,510`
- Shard index: `42`
- Logical CID: `mmrf-shard:21f6d5db475cd231bfa872143093bfba102dc7f0e00320307057ee782fa29cda`
- Candidate manifest SHA-256: `5899a37141cac51af7fa87881d10b190b528e125ee1c74f059c081dd39ccd491`

- Prior candidate manifest SHA-256: `8d0ea8c9f54a05a385e4880f57e86e56c23f25ab5464ceeb0063ba3f61333d26`

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
