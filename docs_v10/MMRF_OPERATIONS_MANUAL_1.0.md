# MMRF v1.0 Operations Manual

## 1. Public installation

```bash
python install/mmrf.py install \
  --project-root . \
  --target /srv/mmrf \
  --profile public-research
```

Verify:

```bash
python install/mmrf.py verify-installation \
  --target /srv/mmrf
```

Run environment diagnostics:

```bash
python install/mmrf.py doctor --project-root /srv/mmrf
```

## 2. Controlled installation

Controlled modules are disabled by default. Create an authorization document
from `config/controlled-authorization.template.json`, set a real approval
reference and a short expiration interval, then run:

```bash
python install/mmrf.py install \
  --project-root . \
  --target /srv/mmrf-controlled \
  --profile controlled-research \
  --controlled-authorization /secure/authorization.json
```

The authorization file is a software gate, not a replacement for identity,
HSM or organizational approval.

## 3. Daily checks

- Verify stable manifest and all shard file hashes.
- Verify installation inventory.
- Check query-audit chain.
- Check latest catalog version per node.
- Confirm no under-replicated shard.
- Confirm all public safety flags remain false.
- Confirm no unexpected private-key files appear under the installation root.

## 4. Dataset promotion ceremony

1. Verify source manifest.
2. Execute declared schema migration.
3. Verify every target logical CID.
4. Submit signed proposal.
5. Run mathematical, security and reproducibility review.
6. Require at least two distinct approvals and no rejection.
7. Publish promotion receipt.
8. Build provenance DAG.
9. Issue stable citation.
10. Freeze a new stable wrapper only for an approved release.

## 5. Backup

Back up independently:

- stable shards;
- stable manifest;
- catalog and governance databases;
- provenance graph;
- citation;
- query audit;
- release public signing key;
- external transparency and witness state.

Do not back up private keys into the public release directory.

## 6. Restore

1. Restore data to an isolated location.
2. Verify release signature and checksums.
3. Verify stable manifest and all shards.
4. Verify governance and provenance bindings.
5. Compare catalog head versions against an external witness.
6. Resume service only after consistency checks pass.

## 7. Incident response

### Shard corruption

- Quarantine the replica.
- Verify a known-good replica by logical CID.
- Copy the shard.
- Publish a new signed catalog version.
- Recalculate replication coverage.

### Signing-key compromise

- Stop promotion and catalog acceptance.
- Revoke the identity through the policy/transparency plane.
- Rotate to a new key epoch.
- Re-sign only new announcements; never rewrite old signed history.

### Unsafe query or export attempt

- Deny the request.
- Preserve the audit event.
- Suspend the session if repeated.
- Review whether multiple aggregate queries can be combined to reconstruct a
  forbidden target-conditioned view.

### Split view

- Stop accepting the affected log or catalog.
- Compare witness heads.
- Preserve both conflicting signed documents.
- Require an explicit governance resolution.

## 8. Upgrade policy

- 1.0.x: bug and security fixes without semantic changes.
- 1.x: backward-compatible additions that preserve all frozen semantics.
- 2.0: required for changes to CID meaning, public safety boundaries,
  reviewer uniqueness, promotion precedence, provenance or citation binding.
