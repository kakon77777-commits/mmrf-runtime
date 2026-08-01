# MMRF v0.5 Federated Vault

A federated encrypted storage and audit-replication layer for MMRF L2/L3
research objects.

Features:

- AES-256-GCM per-object encryption;
- recipient-specific X25519/HKDF DEK wrapping;
- Ed25519 node identity;
- content-addressed encrypted envelopes;
- software-attestation protocol prototype;
- signed monotonic audit checkpoints;
- incremental cross-node replication;
- rollback, replay, fork and tamper rejection;
- local KMS adapter plus a PKCS#11/HSM interface boundary.

No private demonstration keys are included in the release archive. The sample
node databases contain ciphertext only.

The attestation is not hardware remote attestation.
