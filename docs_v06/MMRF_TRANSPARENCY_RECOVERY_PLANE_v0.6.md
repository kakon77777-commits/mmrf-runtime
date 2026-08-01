# MMRF v0.6 Transparency & Recovery Plane

## Transparency

The plane publishes node registration, key rotation, revocation and recovery
events into an append-only Merkle log. Every Signed Tree Head is signed by the
log and co-signed by a configurable witness quorum.

Witnesses retain their last observed tree size, root and STH hash. They reject:

- smaller tree sizes;
- conflicting roots at the same tree size;
- forward heads that do not chain to the previously witnessed STH;
- roots that do not reproduce from the supplied entries.

## Stable AAD and re-wrapping

The v0.6 object format separates immutable payload metadata from recipient
DEK wraps. Recipient changes therefore preserve the encrypted payload:

\[
\text{ciphertext}_{t+1}=\text{ciphertext}_t.
\]

Only the DEK wrap set, re-wrap generation, predecessor CID and signature change.

## Revocation

A revoked node is removed from the current trust state and from future
recipient wrap sets. Revocation cannot revoke knowledge already copied before
the revocation event.

## Recovery

The local prototype encrypts a node X25519 private-key backup under a random
AES-256-GCM recovery secret. That secret is split with a 3-of-5 Shamir scheme.

A recovery event publishes only:

- threshold metadata;
- recovery manifest hash;
- the new node descriptor;
- evidence that threshold reconstruction completed.

Shares and recovered private material are excluded from the release.

## Production gaps

A stable deployment still requires:

- independent log and witness hosts;
- witness gossip;
- mTLS transport;
- HSM/KMS-bound private keys;
- hardware attestation;
- formal recovery ceremonies;
- external immutable backups;
- revocation-latency objectives.
