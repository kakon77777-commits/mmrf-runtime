# MMRF Prime Expansion Handoff — 2026-08-14

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[3,200,000, 3,300,000)`
- Base generation: `2`
- Candidate generation: `15`
- New primes: `6,691`
- Shard index: `32`
- Logical CID: `mmrf-shard:73b52a277c40d44d1e25a9068a2aa7ce0fb8af44460aa6bf0587cadcc0ba0bcb`
- Candidate manifest SHA-256: `b8814728cd281755d11f3e8bb078145f159719dad96b4ff0c195377fdc95736c`

- Prior candidate manifest SHA-256: `ad5b7a51073bb31112e7e2bf00f91bb5107a4dd2f0da1578a6c353a5b101324d`

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
