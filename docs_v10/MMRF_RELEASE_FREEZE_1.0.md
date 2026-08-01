# MMRF v1.0 Release Freeze

## Frozen release identity

```text
MMRF-1.0.0
Stable dataset: a5caea22a57efaac915c00dd92c655b1126e0b6d9b2b93790e48bc167733e0d1
Candidate dataset: 73015c5329ae71900ef3f4aca7f35152f3d96a435e65e3bddbd1ae513d597420
Promotion receipt: 6ad7c85305f45cef095f72eb55ae9f097d9a70388615e5f609fbb83f024c0658
Provenance graph: ffb6dd8d5f7e5e54a559d38a09e1262933e5898f7151627174836624448fd238
Citation: c8b87bbc7a1dde104a202d613c275650be7caa482e9f3d6ad3ca93a3f3e83146
```

## Frozen contracts

1. Logical CID meaning.
2. Stable public classification.
3. Aggregate-only query surface.
4. Safety-gate precedence.
5. Distinct-reviewer quorum.
6. Promotion-receipt binding.
7. Provenance DAG.
8. Citation binding.
9. Controlled components disabled by default.
10. No private keys in release artifacts.

## Change classification

| Change | Version class |
|---|---|
| Documentation correction | Patch |
| Performance optimization with identical output hashes | Patch |
| New aggregate query with no target input | Minor plus security review |
| New public shard column with migration and governance | Minor |
| CID semantic change | Major |
| Allowing target integers or RSA moduli | Major and separate security project |
| Weakening reviewer uniqueness | Major |
| Allowing L2/L3 promotion into public profile | Prohibited under 1.x |

## Release evidence

The signed release manifest covers stable code, schemas, documentation, data,
installation tooling and configuration. Generated benchmark evidence is
hash-addressed separately in the release summary so runtime timing variation
does not change the stable release identity.
