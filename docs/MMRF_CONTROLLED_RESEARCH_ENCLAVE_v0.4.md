# MMRF v0.4 Controlled Research Enclave

## Two separate approvals

MMRF v0.4 separates:

1. permission to enter a controlled workspace;
2. permission for a result to leave the workspace.

A valid L2 session requires independent Ed25519 approvals from:

- `data_owner`;
- `security`.

An export requires a new pair of approvals bound to the exact export request.
Session approval is not export approval.

## Approval token binding

Every token is bound to:

- requester;
- subject type;
- session or export identifier;
- dataset identifier;
- purpose hash;
- allowed operations;
- validity interval;
- nonce.

Tokens are single-use. Replaying a token is rejected.

## Controlled operations

The current prototype allows only:

- certificate integrity summary;
- factor bit-length histogram;
- route-family summary;
- research-run summary;
- internal certificate re-verification.

It does not accept an arbitrary integer, RSA modulus, factor candidate, residue
filter or range-narrowing request.

## Data non-egress

All operation results are first written to the enclave database as
`L2_CONTROLLED`.

Internal re-verification results are explicitly non-exportable.

Exportable aggregate results must pass:

1. structural forbidden-key scanning;
2. exact sensitive-value scanning;
3. data-owner approval;
4. security approval;
5. final re-scan;
6. receipt generation.

Only after all six steps is a JSON file written to `exports/approved`.

## Prototype boundary

This runtime models authorization and information flow. A production enclave
still needs:

- separate process and host isolation;
- encrypted controlled storage;
- KMS/HSM-backed signing keys;
- identity provider integration;
- network egress denial;
- OS sandboxing;
- remote attestation;
- off-host immutable audit replication;
- human export-review user interface.
