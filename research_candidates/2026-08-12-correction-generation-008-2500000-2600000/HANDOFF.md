# MMRF Prime Expansion Handoff — 2026-08-12

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[2,500,000, 2,600,000)`
- Base generation: `2`
- Candidate generation: `8`
- New primes: `6,808`
- Shard index: `25`
- Logical CID: `mmrf-shard:763d684b0e6cb1ee5d278af95274140e24377d4a7d76c49ad6e7e6793c312a1a`
- Candidate manifest SHA-256: `1bf193cf2b37dad69423a7eec5e53a9158b185654c35463829cb66de18aa83cc`

- Prior candidate manifest SHA-256: `029a3134f17b92b508599bcc044de9795aa91827f2385667c1ff0a06e07cb542`

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
