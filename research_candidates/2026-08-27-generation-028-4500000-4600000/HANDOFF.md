# MMRF Prime Expansion Handoff — 2026-08-27

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[4,500,000, 4,600,000)`
- Base generation: `2`
- Candidate generation: `28`
- New primes: `6,493`
- Shard index: `45`
- Logical CID: `mmrf-shard:6e83b9d17023367f326699345c8b9bbfb848dff973869f7387de9d38e2b2c853`
- Candidate manifest SHA-256: `af9fc0e7a843ba597a164444bbd0e8e4279603ee4529e53607cd42ae83715a3f`

- Prior candidate manifest SHA-256: `f2cd9f7047da23fd5788acc3a5dd41a833cbd07cc86df504cc264021843b70fa`

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
