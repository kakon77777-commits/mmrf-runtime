# MMRF Prime Expansion Handoff — 2026-08-15

Status: `CANDIDATE_UNPROMOTED`

Catch-up execution note: this artifact was generated on 2026-08-20 while restoring the paused daily relay. The 2026-08-15 heading and `created_on` / `as-of` values are logical relay dates, not claims that the artifact physically existed on that date.

## Completed unit

- Range: `[3,300,000, 3,400,000)`
- Base generation: `2`
- Candidate generation: `16`
- New primes: `6,639`
- Shard index: `33`
- Logical CID: `mmrf-shard:9123f8583bcae7ed4dcb7040399811288bff869a3c646e04a4d332473f4037c9`
- Candidate manifest SHA-256: `da44e8d0150826d00318ff1c35683a8a851af21afd4ce31a6feff87ebbf63c6a`

- Prior candidate manifest SHA-256: `b8814728cd281755d11f3e8bb078145f159719dad96b4ff0c195377fdc95736c`

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
