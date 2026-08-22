# MMRF Prime Expansion Handoff — 2026-08-22

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[4,000,000, 4,100,000)`
- Base generation: `2`
- Candidate generation: `23`
- New primes: `6,628`
- Shard index: `40`
- Logical CID: `mmrf-shard:25959d0ac7d9f0fd294897f060128411b6bffffd182a1c9e456fa5ecf2e7ea06`
- Candidate manifest SHA-256: `83e83b3de6da2a2fa6a8e29a60958685645373def0a4aee5b3ef7467fc97a546`

- Prior candidate manifest SHA-256: `f346e629e66e37988b42001f044c5430dfadf934fe4a9df1dd63f88c8efdc49b`

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
