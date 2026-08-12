# MMRF Prime Expansion Handoff — 2026-08-12

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[2,600,000, 2,700,000)`
- Base generation: `2`
- Candidate generation: `9`
- New primes: `6,765`
- Shard index: `26`
- Logical CID: `mmrf-shard:be7a8e6d39d2218d3816850c05f9abffa3fef91661f8888e73f0d56921777efd`
- Candidate manifest SHA-256: `b7a0ac28a054ee22b2e14978a8eb4ba7d334b2bd10f0bbd644513ed94e8c8b79`

- Prior candidate manifest SHA-256: `1bf193cf2b37dad69423a7eec5e53a9158b185654c35463829cb66de18aa83cc`

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
