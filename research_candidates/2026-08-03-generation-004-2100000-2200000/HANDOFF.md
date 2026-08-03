# MMRF Prime Expansion Handoff — 2026-08-03

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[2,100,000, 2,200,000)`
- Base generation: `2`
- Candidate generation: `4`
- New primes: `6,857`
- Shard index: `21`
- Logical CID: `mmrf-shard:ab5c1ac0192cafd22d74917e75e0c741e30043df8fd6f0acc2e6ae159ff56a72`
- Candidate manifest SHA-256: `5e63aefb0fcee29011d1c5d94cc798d0841ada67c217754750dd242fc55a9513`

- Prior candidate manifest SHA-256: `3e801ad3751ff3f67e41febb901955ab307235453cbb31c3cb14b570f12bcf5c`

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
