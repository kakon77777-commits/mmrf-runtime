# MMRF v0.6 Transparency & Recovery Plane

This release adds:

- append-only Merkle transparency log;
- signed tree heads;
- 2-of-3 witness quorum;
- inclusion proofs;
- key epochs and continuity-signed rotation;
- node revocation;
- ciphertext-preserving recipient re-wrap;
- 3-of-5 Shamir disaster recovery;
- recovery descriptor publication;
- rollback and split-view detection.

The package contains no private keys or recovery shares and exposes no RSA
target or factor-candidate interface.
