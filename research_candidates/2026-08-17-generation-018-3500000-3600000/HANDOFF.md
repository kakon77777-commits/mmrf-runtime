# MMRF Prime Expansion Handoff — 2026-08-17

Status: `CANDIDATE_UNPROMOTED`

Catch-up execution note: this artifact was generated on 2026-08-20 while restoring the paused daily relay. The 2026-08-17 heading and `created_on` / `as-of` values are logical relay dates, not claims that the artifact physically existed on that date.

## Completed unit

- Range: `[3,500,000, 3,600,000)`
- Base generation: `2`
- Candidate generation: `18`
- New primes: `6,576`
- Shard index: `35`
- Logical CID: `mmrf-shard:01934cae83ad29ab0f0dce030d9953d2a28c26903e2c44845118c5c33771f058`
- Candidate manifest SHA-256: `a124798484f01a773dabb090c5fb490c8ed85f6f3c7ceeff7c5ba6a64ccb436f`

- Prior candidate manifest SHA-256: `63e04c2f64eec8a77a928297e009ba11527cf1b0173641d6d2eea226cb127d63`

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
