# MMRF Prime Expansion Handoff — 2026-08-18

Status: `CANDIDATE_UNPROMOTED`

Catch-up execution note: this artifact was generated on 2026-08-20 while restoring the paused daily relay. The 2026-08-18 heading and `created_on` / `as-of` values are logical relay dates, not claims that the artifact physically existed on that date.

## Completed unit

- Range: `[3,600,000, 3,700,000)`
- Base generation: `2`
- Candidate generation: `19`
- New primes: `6,671`
- Shard index: `36`
- Logical CID: `mmrf-shard:3c28d9f65949aa7a5067b6dd80ed4cd9caa8bf914118d0273f33285f984ad6cf`
- Candidate manifest SHA-256: `ea0c7a0f6caf8771b69a2d6b7a519994f68b0bafdc19bcbbc7838d88da7f1e54`

- Prior candidate manifest SHA-256: `a124798484f01a773dabb090c5fb490c8ed85f6f3c7ceeff7c5ba6a64ccb436f`

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
