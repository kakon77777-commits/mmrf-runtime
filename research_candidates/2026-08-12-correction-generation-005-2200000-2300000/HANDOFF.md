# MMRF Prime Expansion Handoff — 2026-08-12

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[2,200,000, 2,300,000)`
- Base generation: `2`
- Candidate generation: `5`
- New primes: `6,849`
- Shard index: `22`
- Logical CID: `mmrf-shard:4c6a99288c5dbc6ffd480c667be93567584969355d161ec0b3db2decdf7de670`
- Candidate manifest SHA-256: `a23e9dd97d2cbd064c41acf775bac8527f8eb61a5575f11f721f652485c53ba8`

- Prior candidate manifest SHA-256: `5e63aefb0fcee29011d1c5d94cc798d0841ada67c217754750dd242fc55a9513`

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
