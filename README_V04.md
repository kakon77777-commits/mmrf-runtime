# MMRF v0.4 Controlled Research Enclave

MMRF v0.4 adds a controlled L2 research workspace with:

- Ed25519 dual approval;
- purpose- and dataset-bound tokens;
- single-use token replay prevention;
- operation allowlisting;
- risk scoring;
- operation budgets and expiry;
- internal result storage;
- export scanning;
- separate dual export approval;
- approved export receipts;
- hash-linked session transcripts.

The prototype never accepts an arbitrary RSA modulus or returns candidate
factors, narrowed ranges or raw source–factor relationships.

Private demo keys under `examples_v04/demo_private_keys` are test-only and
must never be used in production.
