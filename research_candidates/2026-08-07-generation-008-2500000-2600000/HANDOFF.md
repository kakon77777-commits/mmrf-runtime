# MMRF Prime Expansion Handoff — 2026-08-07

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[2,500,000, 2,600,000)`
- Base generation: `2`
- Candidate generation: `8`
- New primes: `6,808`
- Shard index: `25`
- Logical CID: `mmrf-shard:bd9af84c603abbeac6b8f3789479ae583fc4ea079a7590bdbf8c885357c8e298`
- Candidate manifest SHA-256: `93a2af608e1c09116019db241b183442beab76cd44ff55353551eb93932b2b87`

- Prior candidate manifest SHA-256: `da29c755da37fe6c75030d964c11825e038677153409722cfb578714375a4e66`

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
