from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import os
import ssl
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def unix_now() -> int:
    return int(time.time())


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def save_private_key(key: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    os.chmod(path, 0o600)


def generate_policy_signing_keypair(
    private_path: Path,
    public_path: Path,
) -> dict:
    private = ed25519.Ed25519PrivateKey.generate()
    save_private_key(private, private_path)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_bytes(
        private.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return {
        "private_key_path": str(private_path),
        "public_key_path": str(public_path),
        "public_key_sha256": sha256_bytes(public_path.read_bytes()),
    }


def load_ed25519_private(path: Path) -> ed25519.Ed25519PrivateKey:
    key = serialization.load_pem_private_key(Path(path).read_bytes(), None)
    if not isinstance(key, ed25519.Ed25519PrivateKey):
        raise TypeError("not Ed25519 private key")
    return key


def load_ed25519_public(path: Path) -> ed25519.Ed25519PublicKey:
    key = serialization.load_pem_public_key(Path(path).read_bytes())
    if not isinstance(key, ed25519.Ed25519PublicKey):
        raise TypeError("not Ed25519 public key")
    return key


def create_policy_snapshot(
    *,
    private_key_path: Path,
    version: int,
    active_nodes: Sequence[str],
    revoked_nodes: Sequence[str],
    allowed_measurements: Sequence[str],
    witness_threshold: int,
    previous_snapshot_sha256: str,
    ttl_seconds: int = 300,
) -> dict:
    now = unix_now()
    active = sorted(set(active_nodes) - set(revoked_nodes))
    revoked = sorted(set(revoked_nodes))
    core = {
        "schema": "mmrf-policy-snapshot-0.7",
        "policy_version": int(version),
        "active_nodes": active,
        "revoked_nodes": revoked,
        "allowed_measurements": sorted(set(allowed_measurements)),
        "witness_threshold": int(witness_threshold),
        "previous_snapshot_sha256": previous_snapshot_sha256,
        "issued_at": now,
        "expires_at": now + int(ttl_seconds),
        "nonce": uuid.uuid4().hex,
        "rsa_target_endpoint": False,
        "factor_candidate_endpoint": False,
        "range_narrowing_endpoint": False,
    }
    signature = load_ed25519_private(private_key_path).sign(
        canonical_json(core).encode("utf-8")
    )
    signed = {**core, "signature_ed25519": b64(signature)}
    return {**signed, "snapshot_sha256": sha256_json(signed)}


def verify_policy_snapshot(
    snapshot: Mapping[str, Any],
    *,
    public_key_path: Path,
    current_snapshot: Optional[Mapping[str, Any]] = None,
    now: Optional[int] = None,
) -> dict:
    now = unix_now() if now is None else int(now)
    try:
        signed = {
            key: value
            for key, value in snapshot.items()
            if key != "snapshot_sha256"
        }
        core = {
            key: value
            for key, value in signed.items()
            if key != "signature_ed25519"
        }
        load_ed25519_public(public_key_path).verify(
            unb64(snapshot["signature_ed25519"]),
            canonical_json(core).encode("utf-8"),
        )
        checks = {
            "schema_ok": snapshot.get("schema") == "mmrf-policy-snapshot-0.7",
            "hash_ok": snapshot.get("snapshot_sha256") == sha256_json(signed),
            "time_ok": int(snapshot["issued_at"]) <= now <= int(snapshot["expires_at"]),
            "node_sets_disjoint": not (
                set(snapshot["active_nodes"]) & set(snapshot["revoked_nodes"])
            ),
            "safety_endpoints_disabled": (
                snapshot.get("rsa_target_endpoint") is False
                and snapshot.get("factor_candidate_endpoint") is False
                and snapshot.get("range_narrowing_endpoint") is False
            ),
        }
        if current_snapshot is not None:
            checks["version_monotonic"] = (
                int(snapshot["policy_version"])
                == int(current_snapshot["policy_version"]) + 1
            )
            checks["chain_ok"] = (
                snapshot["previous_snapshot_sha256"]
                == current_snapshot["snapshot_sha256"]
            )
        else:
            checks["version_monotonic"] = int(snapshot["policy_version"]) >= 1
            checks["chain_ok"] = (
                snapshot["previous_snapshot_sha256"] == "0" * 64
            )
        return {
            "valid": all(checks.values()),
            "checks": checks,
            "reason": None if all(checks.values()) else "policy_claim_mismatch",
        }
    except Exception as exc:
        return {
            "valid": False,
            "checks": {},
            "reason": f"policy_signature_or_structure_invalid:{type(exc).__name__}",
        }


def generate_ca(
    *,
    private_key_path: Path,
    certificate_path: Path,
    common_name: str = "MMRF Test Root CA",
    valid_days: int = 30,
) -> dict:
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name)
    ])
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=valid_days))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=1),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(
                key.public_key()
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    save_private_key(key, private_key_path)
    certificate_path.parent.mkdir(parents=True, exist_ok=True)
    certificate_path.write_bytes(
        certificate.public_bytes(serialization.Encoding.PEM)
    )
    return {
        "private_key_path": str(private_key_path),
        "certificate_path": str(certificate_path),
        "certificate_sha256": sha256_bytes(certificate_path.read_bytes()),
    }


def issue_mtls_certificate(
    *,
    ca_private_key_path: Path,
    ca_certificate_path: Path,
    common_name: str,
    private_key_path: Path,
    certificate_path: Path,
    valid_days: int = 7,
) -> dict:
    ca_key = serialization.load_pem_private_key(
        Path(ca_private_key_path).read_bytes(), None
    )
    ca_cert = x509.load_pem_x509_certificate(
        Path(ca_certificate_path).read_bytes()
    )
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, common_name)
    ])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=valid_days))
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            ]),
            critical=False,
        )
        .add_extension(
            x509.ExtendedKeyUsage([
                ExtendedKeyUsageOID.SERVER_AUTH,
                ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=False,
        )
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(
                ca_key.public_key()
            ),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    save_private_key(key, private_key_path)
    certificate_path.parent.mkdir(parents=True, exist_ok=True)
    certificate_path.write_bytes(
        certificate.public_bytes(serialization.Encoding.PEM)
    )
    return {
        "common_name": common_name,
        "private_key_path": str(private_key_path),
        "certificate_path": str(certificate_path),
        "certificate_sha256": sha256_bytes(certificate_path.read_bytes()),
    }


def create_server_ssl_context(
    *,
    ca_certificate_path: Path,
    certificate_path: Path,
    private_key_path: Path,
) -> ssl.SSLContext:
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(cafile=str(ca_certificate_path))
    context.load_cert_chain(
        certfile=str(certificate_path),
        keyfile=str(private_key_path),
    )
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context


def create_client_ssl_context(
    *,
    ca_certificate_path: Path,
    certificate_path: Path,
    private_key_path: Path,
) -> ssl.SSLContext:
    context = ssl.create_default_context(
        ssl.Purpose.SERVER_AUTH,
        cafile=str(ca_certificate_path),
    )
    context.load_cert_chain(
        certfile=str(certificate_path),
        keyfile=str(private_key_path),
    )
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = True
    return context


def https_json(
    *,
    url: str,
    ssl_context: ssl.SSLContext,
    method: str = "GET",
    payload: Optional[Mapping[str, Any]] = None,
    timeout: float = 5.0,
) -> tuple[int, dict, float]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = canonical_json(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers=headers,
    )
    started = time.perf_counter_ns()
    try:
        with urllib.request.urlopen(
            request,
            context=ssl_context,
            timeout=timeout,
        ) as response:
            body = response.read()
            elapsed = (time.perf_counter_ns() - started) / 1_000_000
            return response.status, json.loads(body), elapsed
    except urllib.error.HTTPError as exc:
        body = exc.read()
        elapsed = (time.perf_counter_ns() - started) / 1_000_000
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"error": body.decode("utf-8", errors="replace")}
        return exc.code, parsed, elapsed


class AttestationAdapter:
    adapter_id = "abstract"

    def verify(
        self,
        evidence: Mapping[str, Any],
        policy: Mapping[str, Any],
    ) -> dict:
        raise NotImplementedError


class SoftwareMeasurementAdapter(AttestationAdapter):
    adapter_id = "software-measurement-v0.7"

    def verify(
        self,
        evidence: Mapping[str, Any],
        policy: Mapping[str, Any],
    ) -> dict:
        measurement = evidence.get("measurement_sha256")
        allowed = measurement in set(policy.get("allowed_measurements", []))
        return {
            "valid": (
                evidence.get("schema") == "mmrf-software-attestation-0.7"
                and isinstance(measurement, str)
                and len(measurement) == 64
                and allowed
            ),
            "adapter": self.adapter_id,
            "measurement_allowed": allowed,
            "hardware_backed": False,
        }


class TPMQuoteAdapter(AttestationAdapter):
    adapter_id = "tpm2-quote-adapter"

    def verify(self, evidence: Mapping[str, Any], policy: Mapping[str, Any]) -> dict:
        raise NotImplementedError("TPM quote verification not installed")


class SEVSNPAdapter(AttestationAdapter):
    adapter_id = "amd-sev-snp-adapter"

    def verify(self, evidence: Mapping[str, Any], policy: Mapping[str, Any]) -> dict:
        raise NotImplementedError("SEV-SNP verification not installed")


class TDXAdapter(AttestationAdapter):
    adapter_id = "intel-tdx-adapter"

    def verify(self, evidence: Mapping[str, Any], policy: Mapping[str, Any]) -> dict:
        raise NotImplementedError("TDX verification not installed")


def node_state_from_policy(
    *,
    node_id: str,
    measurement_sha256: str,
    policy: Mapping[str, Any],
) -> dict:
    attestation = SoftwareMeasurementAdapter().verify(
        {
            "schema": "mmrf-software-attestation-0.7",
            "node_id": node_id,
            "measurement_sha256": measurement_sha256,
        },
        policy,
    )
    if node_id in set(policy.get("revoked_nodes", [])):
        status = "REVOKED"
        reason = "node_revoked_by_policy"
    elif not attestation["valid"]:
        status = "QUARANTINED"
        reason = "attestation_not_allowed"
    elif node_id in set(policy.get("active_nodes", [])):
        status = "ACTIVE"
        reason = None
    else:
        status = "UNREGISTERED"
        reason = "node_not_active"
    return {
        "node_id": node_id,
        "status": status,
        "reason": reason,
        "policy_version": policy["policy_version"],
        "policy_snapshot_sha256": policy["snapshot_sha256"],
        "attestation": attestation,
        "updated_at": utc_now(),
        "updated_monotonic_ns": time.monotonic_ns(),
    }


FORBIDDEN_REPLICATION_FIELDS = {
    "rsa_modulus",
    "public_key",
    "private_key",
    "factor",
    "factors",
    "candidate",
    "candidates",
    "range_narrowing",
    "source_integer",
    "prime_decimal",
}


def validate_replication_message(
    message: Mapping[str, Any],
    *,
    peer_common_name: str,
    recipient_node_id: str,
    policy: Mapping[str, Any],
) -> dict:
    forbidden = sorted(set(message) & FORBIDDEN_REPLICATION_FIELDS)
    checks = {
        "schema_ok": message.get("schema") == "mmrf-network-replication-0.7",
        "peer_binding_ok": message.get("source_node_id") == peer_common_name,
        "source_active": peer_common_name in set(policy.get("active_nodes", [])),
        "source_not_revoked": peer_common_name not in set(policy.get("revoked_nodes", [])),
        "recipient_active": recipient_node_id in set(policy.get("active_nodes", [])),
        "recipient_not_revoked": recipient_node_id not in set(policy.get("revoked_nodes", [])),
        "recipient_list_ok": recipient_node_id in set(
            message.get("recipient_node_ids", [])
        ),
        "ciphertext_hash_ok": (
            isinstance(message.get("ciphertext"), str)
            and message.get("ciphertext_sha256")
            == sha256_bytes(message["ciphertext"].encode("ascii"))
        ),
        "forbidden_fields_absent": not forbidden,
        "encrypted_only": message.get("encrypted_payload") is True,
    }
    return {
        "valid": all(checks.values()),
        "checks": checks,
        "forbidden_fields": forbidden,
        "reason": None if all(checks.values()) else "replication_policy_rejected",
    }
