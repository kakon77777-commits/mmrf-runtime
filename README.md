# MMRF v1.0 Stable Research Infrastructure

MMRF v1.0 freezes the first stable public research profile.

```text
Stable dataset manifest:
a5caea22a57efaac915c00dd92c655b1126e0b6d9b2b93790e48bc167733e0d1

Prime count:
148,933

Shards:
20
```

## Quick verification

```bash
python install/mmrf.py verify-release --project-root .
python install/mmrf.py doctor --project-root .
```

## Public installation

```bash
python install/mmrf.py install   --project-root .   --target ./installed-mmrf   --profile public-research
```

The default installation exposes aggregate mathematical research only.
Controlled Enclave and Vault source modules require an explicit authorization
file and include no private keys or controlled datasets.

## Prime expansion candidates

The stable v1.0 dataset is frozen. An append-only expansion candidate can be
generated without changing it:

```bash
python workflows/prime_expansion_candidate.py --as-of YYYY-MM-DD
```

The workflow writes an unpromoted candidate shard, a candidate manifest, an
independent verification record, and `HANDOFF.md` under `research_candidates/`.
It checks the next non-overlapping 100,000-value range with both a NumPy sieve
and a separate Python segmented sieve. A candidate is not a public stable
generation until independent review and the existing MMRF governance chain are
complete.
