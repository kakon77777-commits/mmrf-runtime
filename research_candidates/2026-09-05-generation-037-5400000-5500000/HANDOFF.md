# MMRF Prime Expansion Handoff — 2026-09-05

Status: `CANDIDATE_UNPROMOTED`

Catch-up provenance: `2026-09-05` is the logical relay date. This artifact was physically generated during the catch-up run on `2026-09-07`; it does not claim to have physically existed on the logical date.

## Completed unit

- Range: `[5,400,000, 5,500,000)`
- Base generation: `2`
- Candidate generation: `37`
- New primes: `6,438`
- Shard index: `54`
- Logical CID: `mmrf-shard:3d83f705a84f7493e55e2632aa66d3c328a90ad208a770cdd725c041ad385691`
- Candidate manifest SHA-256: `f9bb26a9cee02638b633300a4e0a3f67746c6b1f650dad493c519072d0956387`

- Prior candidate manifest SHA-256: `bfe78c6145f14b7ef0b8c43cc14c6fc62f5bda20b40681c8900c8a11ef9a7ec9`

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
