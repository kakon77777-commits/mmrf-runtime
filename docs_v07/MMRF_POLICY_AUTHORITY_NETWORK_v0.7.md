# MMRF v0.7 Policy Authority & Real Network Trial

## Trust layers

MMRF v0.7 separates four forms of trust:

1. **PKI trust** — mTLS proves possession of a CA-issued certificate.
2. **Policy trust** — a signed, monotonic policy snapshot says whether a node
   is currently active or revoked.
3. **Attestation trust** — the node measurement must be accepted by policy.
4. **Message trust** — every operation must match a narrow allowlisted shape.

A certificate that has not expired is not sufficient authorization.

## Real network trial

The benchmark starts separate localhost processes for:

- one Policy Authority;
- three node agents;
- three Witness gossip services.

All HTTP traffic is TLS with mandatory client certificates. The benchmark
performs actual socket connections rather than in-process function calls.

## Policy propagation

Node agents poll the Authority for signed snapshots. Each update must:

- verify the Ed25519 signature;
- increment the policy version by exactly one;
- chain to the prior snapshot hash;
- remain within its validity interval;
- keep active and revoked node sets disjoint;
- keep RSA target, factor candidate and range-narrowing endpoints disabled.

## Revocation

Revoking a node has two independent effects:

- a revoked recipient rejects new replication;
- active recipients reject a revoked sender even if its mTLS certificate is
  still valid.

Revocation does not remotely erase data already obtained before propagation.

## Witness gossip

Witnesses accept signed tree heads over mTLS and independently preserve the
highest observed tree size and root. They reject:

- rollback;
- same-size split views;
- invalid roots;
- broken STH chains.

## Attestation

The implemented adapter verifies a software measurement allowlist. TPM 2.0,
AMD SEV-SNP and Intel TDX adapters exist as explicit unimplemented boundaries.
The current result is not hardware-backed attestation.

## Production gaps

The trial still uses localhost and test certificates. Stable deployment needs:

- independent hosts and administrative domains;
- production CA lifecycle and OCSP/CRL;
- HSM-bound authority and TLS keys;
- persistent service supervision;
- independent Witness operators;
- hardware attestation;
- revocation latency SLOs and alerting;
- denial-of-service controls.
