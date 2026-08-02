# MMRF Prime Expansion Handoff — 2026-08-02

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[2,000,000, 2,100,000)`
- Base generation: `2`
- Candidate generation: `3`
- New primes: `6,872`
- Shard index: `20`
- Logical CID: `mmrf-shard:a3e7b2ed1e5c339e9cf036df566c87a129bc71b12f5d4fcf3159bde45f13c6f2`
- Candidate manifest SHA-256: `3e801ad3751ff3f67e41febb901955ab307235453cbb31c3cb14b570f12bcf5c`

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
