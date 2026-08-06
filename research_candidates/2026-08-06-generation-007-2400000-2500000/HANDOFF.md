# MMRF Prime Expansion Handoff — 2026-08-06

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[2,400,000, 2,500,000)`
- Base generation: `2`
- Candidate generation: `7`
- New primes: `6,770`
- Shard index: `24`
- Logical CID: `mmrf-shard:851374307b748c385de760ed78d085a182bffebbd8119c011150e3f431b1d556`
- Candidate manifest SHA-256: `da29c755da37fe6c75030d964c11825e038677153409722cfb578714375a4e66`

- Prior candidate manifest SHA-256: `81cc8ce7cdfa40bac836a9e279204192e8bf5e6f15cea7b6a9a12dd82b8ecb14`

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
