# MMRF Prime Expansion Handoff — 2026-08-13

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[3,100,000, 3,200,000)`
- Base generation: `2`
- Candidate generation: `14`
- New primes: `6,717`
- Shard index: `31`
- Logical CID: `mmrf-shard:79da7246348ace955607a16fc19e520080cb7ad6500d637840bc8067c6a9381d`
- Candidate manifest SHA-256: `ad5b7a51073bb31112e7e2bf00f91bb5107a4dd2f0da1578a6c353a5b101324d`

- Prior candidate manifest SHA-256: `370be6de9ffd94b2b121e1199d274aa90584379a6c83bd602b60cdaee34db157`

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
