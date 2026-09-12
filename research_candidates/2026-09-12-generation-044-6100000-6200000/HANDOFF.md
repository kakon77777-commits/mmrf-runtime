# MMRF Prime Expansion Handoff — 2026-09-12

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[6,100,000, 6,200,000)`
- Base generation: `2`
- Candidate generation: `44`
- New primes: `6,402`
- Shard index: `61`
- Logical CID: `mmrf-shard:1656ad15ea16fd91040421334702645c7fae7226695dd2e14a3bf5432b81830f`
- Candidate manifest SHA-256: `7906a9a88f0718f4426881f3d63310c4d84c18c42056ed15cfac60ab402683c2`

- Prior candidate manifest SHA-256: `e7942517ca98ed75c83bdbb9cad1e93b753f9293c8752858bdbb8d9d04d0ff57`

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
