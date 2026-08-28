# MMRF Prime Expansion Handoff — 2026-08-28

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[4,600,000, 4,700,000)`
- Base generation: `2`
- Candidate generation: `29`
- New primes: `6,523`
- Shard index: `46`
- Logical CID: `mmrf-shard:b5e2cb663a1ecd47a4301848f8f8ecb7dd51236d6f0f688ac60e1cebdc10045c`
- Candidate manifest SHA-256: `73202525d48470b405943930fb050147e8658bedc10f069b77b141de22df5fed`

- Prior candidate manifest SHA-256: `af9fc0e7a843ba597a164444bbd0e8e4279603ee4529e53607cd42ae83715a3f`

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
