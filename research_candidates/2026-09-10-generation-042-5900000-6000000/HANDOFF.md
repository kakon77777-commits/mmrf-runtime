# MMRF Prime Expansion Handoff — 2026-09-10

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[5,900,000, 6,000,000)`
- Base generation: `2`
- Candidate generation: `42`
- New primes: `6,420`
- Shard index: `59`
- Logical CID: `mmrf-shard:620ddf188a2dfc0f5847866ad3eb1286d85001c084bd7dd348370bae3e86266b`
- Candidate manifest SHA-256: `b10f9b6f1a7f5097b4747f9a19d43da74110bb594d612c43d228ecd3db6f55ec`

- Prior candidate manifest SHA-256: `708deab36f8c34fff0e056795f4af1790f6f09f586d80c0cf88a62817abafdde`

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
