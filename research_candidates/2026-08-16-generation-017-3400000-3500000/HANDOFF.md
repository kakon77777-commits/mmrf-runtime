# MMRF Prime Expansion Handoff — 2026-08-16

Status: `CANDIDATE_UNPROMOTED`

Catch-up execution note: this artifact was generated on 2026-08-20 while restoring the paused daily relay. The 2026-08-16 heading and `created_on` / `as-of` values are logical relay dates, not claims that the artifact physically existed on that date.

## Completed unit

- Range: `[3,400,000, 3,500,000)`
- Base generation: `2`
- Candidate generation: `17`
- New primes: `6,611`
- Shard index: `34`
- Logical CID: `mmrf-shard:eace7970106513c446c720fff2cd61377f35402b8ff2a74a8c1860a2e27b3907`
- Candidate manifest SHA-256: `63e04c2f64eec8a77a928297e009ba11527cf1b0173641d6d2eea226cb127d63`

- Prior candidate manifest SHA-256: `da44e8d0150826d00318ff1c35683a8a851af21afd4ce31a6feff87ebbf63c6a`

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
