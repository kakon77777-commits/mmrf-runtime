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
