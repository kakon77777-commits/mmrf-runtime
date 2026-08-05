# MMRF Prime Expansion Handoff — 2026-08-04

Status: `CANDIDATE_UNPROMOTED`

## Completed unit

- Range: `[2,200,000, 2,300,000)`
- Base generation: `2`
- Candidate generation: `5`
- New primes: `6,849`
- Shard index: `22`
- Logical CID: `mmrf-shard:3d4cc20a03d2be265bffa5071f9801ceb5b0838634df2af2c9f1cfb8cb743f42`
- Candidate manifest SHA-256: `9ab2b083590dcaac0bdfa65ca8c1c22bea758223b3e4479c16288055ab771847`

- Prior candidate manifest SHA-256: `5e63aefb0fcee29011d1c5d94cc798d0841ada67c217754750dd242fc55a9513`

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
