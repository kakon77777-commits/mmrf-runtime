# MMRF Prime Expansion Handoff — 2026-09-09

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[5,800,000, 5,900,000)`
- Base generation: `2`
- Candidate generation: `41`
- New primes: `6,436`
- Shard index: `58`
- Logical CID: `mmrf-shard:c64b296c8af6a2785bd4ccfdc8eb8cc105baa61597eb1dc44429ce861d1964d9`
- Candidate manifest SHA-256: `708deab36f8c34fff0e056795f4af1790f6f09f586d80c0cf88a62817abafdde`

- Prior candidate manifest SHA-256: `3dea65d86808923707db1cc73dc6ad703364bd94a9408c8561562ba51503ee3d`

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
