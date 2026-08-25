# MMRF Prime Expansion Handoff — 2026-08-25

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[4,300,000, 4,400,000)`
- Base generation: `2`
- Candidate generation: `26`
- New primes: `6,511`
- Shard index: `43`
- Logical CID: `mmrf-shard:e59652f788fa021e705b5885277334ae3d47bdf2380f8fb05adbac664dc6f576`
- Candidate manifest SHA-256: `f069e7cd2ffd8ce928a4966d31fe35d610e71fe7a535ad5f3e5d1aee178bcc56`

- Prior candidate manifest SHA-256: `5899a37141cac51af7fa87881d10b190b528e125ee1c74f059c081dd39ccd491`

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
