# MMRF v0.5 Federated Vault

## Cryptographic model

Each object uses a random 256-bit data-encryption key and AES-256-GCM. The DEK
is wrapped separately for every authorized node using X25519, HKDF-SHA256 and
AES-256-GCM. Nodes do not share one global data key.

Node identity and synchronization signatures use Ed25519. Encryption and
identity keys are separate.

## KMS/HSM boundary

`LocalX25519KMS` is a local prototype adapter. `PKCS11HSMAdapter` declares the
production boundary but intentionally contains no fake HSM implementation.
Production private keys must be non-exportable and held by a KMS/HSM.

## Software attestation boundary

The v0.5 attestation is a signed software claim containing a measurement hash,
configuration hash, boot nonce and expiry. It is useful for protocol testing,
but it is not hardware remote attestation and cannot prove host integrity
against a compromised operating system.

## Content-addressed encrypted objects

The public CID is calculated over encrypted object metadata, ciphertext and
recipient wraps. The plaintext digest is sealed inside the encrypted payload,
so the outer object does not expose plaintext equality.

## Replication

A replication bundle contains:

- an origin attestation;
- a signed monotonic checkpoint;
- the audit segment since the peer's last accepted sequence;
- encrypted objects addressed to the recipient;
- an origin signature over the entire bundle.

The receiving node checks trust, attestation, signatures, checkpoint
monotonicity, audit continuity, object CID and recipient authorization before
committing anything.

## Rollback and fork resistance

Peers remember the last accepted checkpoint hash and sequence. Older,
replayed, skipped or forked checkpoints are rejected. This detects protocol
rollback; it does not replace an external transparency log or consensus
system.

## Cryptography safety boundary

The vault stores and replicates encrypted research objects only. It exposes no
RSA target, factor-candidate or range-narrowing API. Replication authorization
is based on object recipients, not on a request to analyze a third-party key.
