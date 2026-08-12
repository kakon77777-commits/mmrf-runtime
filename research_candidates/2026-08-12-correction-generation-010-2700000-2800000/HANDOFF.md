# MMRF Prime Expansion Handoff — 2026-08-12

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[2,700,000, 2,800,000)`
- Base generation: `2`
- Candidate generation: `10`
- New primes: `6,717`
- Shard index: `27`
- Logical CID: `mmrf-shard:f30ac19830edd5563329ed1f69c5e426d1f52c37361939d7b94132a0f11e9b9c`
- Candidate manifest SHA-256: `57f026da358fc38164e4a905d81622003b46a18b4d4bd342bc440c003393e3a4`

- Prior candidate manifest SHA-256: `b7a0ac28a054ee22b2e14978a8eb4ba7d334b2bd10f0bbd644513ed94e8c8b79`

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
