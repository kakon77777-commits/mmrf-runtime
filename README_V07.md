# MMRF v0.7 Policy Authority & Real Network Trial

This release adds:

- independent signed Policy Authority snapshots;
- a test root CA and mandatory mTLS;
- three separate node-agent processes;
- three separate Witness gossip processes;
- policy-chain verification;
- revocation propagation measurement;
- revoked-sender and revoked-recipient enforcement;
- encrypted-only replication messages;
- software attestation and hardware-adapter boundaries.

The release ZIP excludes CA private keys, policy-signing private keys and all
service private keys.
