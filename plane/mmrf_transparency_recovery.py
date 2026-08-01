from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from mmrf_federated_vault import (
    b64,
    unb64,
    canonical_json,
    sha256_bytes,
    sha256_json,
    raw_ed25519_public,
    raw_x25519_public,
    load_ed25519_public,
    load_x25519_public,
    save_private_key,
    load_ed25519_private,
    load_x25519_private,
)


SHAMIR_PRIME = (1 << 521) - 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def unix_now() -> int:
    return int(time.time())


def generate_epoch_node_material(
    *,
    node_id: str,
    key_epoch: int,
    private_dir: Path,
    public_dir: Path,
    roles: Sequence[str],
    accepted_measurements: Sequence[str],
    previous_descriptor_sha256: Optional[str] = None,
) -> dict:
    identity_private = ed25519.Ed25519PrivateKey.generate()
    encryption_private = x25519.X25519PrivateKey.generate()
    identity_path = private_dir / f"{node_id}.epoch{key_epoch}.identity.private.pem"
    encryption_path = private_dir / f"{node_id}.epoch{key_epoch}.encryption.private.pem"
    save_private_key(identity_private, identity_path)
    save_private_key(encryption_private, encryption_path)

    core = {
        "schema": "mmrf-node-descriptor-0.6",
        "node_id": node_id,
        "key_epoch": int(key_epoch),
        "roles": sorted(set(roles)),
        "identity_public_ed25519": raw_ed25519_public(
            identity_private.public_key()
        ),
        "encryption_public_x25519": raw_x25519_public(
            encryption_private.public_key()
        ),
        "accepted_measurements": sorted(set(accepted_measurements)),
        "previous_descriptor_sha256": previous_descriptor_sha256,
        "created_at": utc_now(),
    }
    descriptor = {**core, "descriptor_sha256": sha256_json(core)}
    public_dir.mkdir(parents=True, exist_ok=True)
    descriptor_path = public_dir / f"{node_id}.epoch{key_epoch}.descriptor.json"
    descriptor_path.write_text(
        json.dumps(descriptor, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "node_id": node_id,
        "key_epoch": key_epoch,
        "identity_private_path": str(identity_path),
        "encryption_private_path": str(encryption_path),
        "descriptor_path": str(descriptor_path),
        "descriptor": descriptor,
    }


def verify_epoch_descriptor(descriptor: Mapping[str, Any]) -> bool:
    core = {
        key: value
        for key, value in descriptor.items()
        if key != "descriptor_sha256"
    }
    return (
        descriptor.get("schema") == "mmrf-node-descriptor-0.6"
        and descriptor.get("descriptor_sha256") == sha256_json(core)
        and int(descriptor.get("key_epoch", 0)) >= 1
    )


def sign_descriptor_continuity(
    new_descriptor: Mapping[str, Any],
    old_identity_private_path: Path,
) -> str:
    return b64(
        load_ed25519_private(old_identity_private_path).sign(
            canonical_json(new_descriptor).encode("utf-8")
        )
    )


def verify_descriptor_continuity(
    new_descriptor: Mapping[str, Any],
    old_descriptor: Mapping[str, Any],
    signature: str,
) -> bool:
    try:
        load_ed25519_public(
            old_descriptor["identity_public_ed25519"]
        ).verify(
            unb64(signature),
            canonical_json(new_descriptor).encode("utf-8"),
        )
        return (
            new_descriptor.get("previous_descriptor_sha256")
            == old_descriptor.get("descriptor_sha256")
            and int(new_descriptor.get("key_epoch", 0))
            == int(old_descriptor.get("key_epoch", 0)) + 1
        )
    except Exception:
        return False


def _leaf_hash(entry: Mapping[str, Any]) -> bytes:
    return hashlib.sha256(
        b"\x00" + canonical_json(entry).encode("utf-8")
    ).digest()


def _node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def merkle_root(entries: Sequence[Mapping[str, Any]]) -> str:
    if not entries:
        return sha256_bytes(b"")
    level = [_leaf_hash(entry) for entry in entries]
    while len(level) > 1:
        next_level: list[bytes] = []
        for index in range(0, len(level), 2):
            left = level[index]
            right = level[index + 1] if index + 1 < len(level) else left
            next_level.append(_node_hash(left, right))
        level = next_level
    return level[0].hex()


def inclusion_proof(
    entries: Sequence[Mapping[str, Any]],
    leaf_index: int,
) -> list[dict]:
    if not (0 <= leaf_index < len(entries)):
        raise IndexError(leaf_index)
    level = [_leaf_hash(entry) for entry in entries]
    index = leaf_index
    proof: list[dict] = []
    while len(level) > 1:
        sibling_index = index - 1 if index % 2 else index + 1
        if sibling_index >= len(level):
            sibling_index = index
        proof.append({
            "side": "left" if sibling_index < index else "right",
            "hash": level[sibling_index].hex(),
        })
        next_level: list[bytes] = []
        for offset in range(0, len(level), 2):
            left = level[offset]
            right = (
                level[offset + 1]
                if offset + 1 < len(level)
                else left
            )
            next_level.append(_node_hash(left, right))
        index //= 2
        level = next_level
    return proof


def verify_inclusion_proof(
    *,
    entry: Mapping[str, Any],
    proof: Sequence[Mapping[str, Any]],
    expected_root: str,
) -> bool:
    current = _leaf_hash(entry)
    for item in proof:
        sibling = bytes.fromhex(item["hash"])
        if item["side"] == "left":
            current = _node_hash(sibling, current)
        elif item["side"] == "right":
            current = _node_hash(current, sibling)
        else:
            return False
    return current.hex() == expected_root


class TransparencyLog:
    def __init__(
        self,
        db_path: Path,
        log_id: str,
        private_key_path: Path,
        public_key_path: Path,
    ):
        self.db_path = Path(db_path)
        self.log_id = log_id
        self.private_key_path = Path(private_key_path)
        self.public_key_path = Path(public_key_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")

    @staticmethod
    def generate_keypair(
        private_key_path: Path,
        public_key_path: Path,
    ) -> dict:
        private = ed25519.Ed25519PrivateKey.generate()
        save_private_key(private, private_key_path)
        public_key_path.parent.mkdir(parents=True, exist_ok=True)
        public_key_path.write_bytes(
            private.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
        return {
            "private_key_path": str(private_key_path),
            "public_key_path": str(public_key_path),
            "public_key_sha256": sha256_bytes(public_key_path.read_bytes()),
        }

    def init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS entries(
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT NOT NULL UNIQUE,
                entry_type TEXT NOT NULL,
                subject_id TEXT NOT NULL,
                entry_json TEXT NOT NULL,
                entry_sha256 TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tree_heads(
                tree_size INTEGER PRIMARY KEY,
                root_hash_sha256 TEXT NOT NULL,
                previous_sth_sha256 TEXT NOT NULL,
                sth_sha256 TEXT NOT NULL UNIQUE,
                sth_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def append(
        self,
        *,
        entry_type: str,
        subject_id: str,
        payload: Mapping[str, Any],
    ) -> dict:
        sequence = self.conn.execute(
            "SELECT COALESCE(MAX(sequence),0)+1 AS n FROM entries"
        ).fetchone()["n"]
        entry = {
            "schema": "mmrf-transparency-entry-0.6",
            "entry_id": f"log-entry:{uuid.uuid4()}",
            "sequence": sequence,
            "entry_type": entry_type,
            "subject_id": subject_id,
            "payload": dict(payload),
            "created_at": utc_now(),
        }
        digest = sha256_json(entry)
        self.conn.execute(
            """
            INSERT INTO entries(
                sequence, entry_id, entry_type, subject_id,
                entry_json, entry_sha256, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sequence,
                entry["entry_id"],
                entry_type,
                subject_id,
                canonical_json(entry),
                digest,
                entry["created_at"],
            ),
        )
        self.conn.commit()
        return entry

    def entries(self, limit: Optional[int] = None) -> list[dict]:
        if limit is None:
            rows = self.conn.execute(
                "SELECT entry_json FROM entries ORDER BY sequence"
            )
        else:
            rows = self.conn.execute(
                """
                SELECT entry_json FROM entries
                WHERE sequence <= ?
                ORDER BY sequence
                """,
                (int(limit),),
            )
        return [json.loads(row["entry_json"]) for row in rows]

    def create_sth(self) -> dict:
        entries = self.entries()
        tree_size = len(entries)
        root_hash = merkle_root(entries)
        previous = self.conn.execute(
            """
            SELECT sth_sha256 FROM tree_heads
            ORDER BY tree_size DESC LIMIT 1
            """
        ).fetchone()
        previous_hash = previous["sth_sha256"] if previous else "0" * 64
        core = {
            "schema": "mmrf-signed-tree-head-0.6",
            "log_id": self.log_id,
            "tree_size": tree_size,
            "root_hash_sha256": root_hash,
            "previous_sth_sha256": previous_hash,
            "created_at": utc_now(),
        }
        signature = b64(
            load_ed25519_private(self.private_key_path).sign(
                canonical_json(core).encode("utf-8")
            )
        )
        signed = {**core, "log_signature_ed25519": signature}
        sth = {**signed, "sth_sha256": sha256_json(signed)}
        existing = self.conn.execute(
            "SELECT root_hash_sha256 FROM tree_heads WHERE tree_size = ?",
            (tree_size,),
        ).fetchone()
        if existing:
            if existing["root_hash_sha256"] != root_hash:
                raise RuntimeError("transparency log equivocation")
            return json.loads(
                self.conn.execute(
                    "SELECT sth_json FROM tree_heads WHERE tree_size = ?",
                    (tree_size,),
                ).fetchone()["sth_json"]
            )
        self.conn.execute(
            """
            INSERT INTO tree_heads(
                tree_size, root_hash_sha256,
                previous_sth_sha256, sth_sha256,
                sth_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                tree_size,
                root_hash,
                previous_hash,
                sth["sth_sha256"],
                canonical_json(sth),
                core["created_at"],
            ),
        )
        self.conn.commit()
        return sth

    def proof(self, sequence: int, tree_size: Optional[int] = None) -> dict:
        entries = self.entries(tree_size)
        index = int(sequence) - 1
        return {
            "sequence": sequence,
            "tree_size": len(entries),
            "entry": entries[index],
            "proof": inclusion_proof(entries, index),
            "root_hash_sha256": merkle_root(entries),
        }


def verify_sth_signature(
    sth: Mapping[str, Any],
    log_public_key_path: Path,
) -> bool:
    try:
        signed = {
            key: value
            for key, value in sth.items()
            if key != "sth_sha256"
        }
        core = {
            key: value
            for key, value in signed.items()
            if key != "log_signature_ed25519"
        }
        key = serialization.load_pem_public_key(
            Path(log_public_key_path).read_bytes()
        )
        if not isinstance(key, ed25519.Ed25519PublicKey):
            return False
        key.verify(
            unb64(sth["log_signature_ed25519"]),
            canonical_json(core).encode("utf-8"),
        )
        return sth.get("sth_sha256") == sha256_json(signed)
    except Exception:
        return False


def generate_witness_material(
    *,
    witness_id: str,
    private_dir: Path,
    public_dir: Path,
) -> dict:
    private = ed25519.Ed25519PrivateKey.generate()
    private_path = private_dir / f"{witness_id}.private.pem"
    save_private_key(private, private_path)
    descriptor = {
        "schema": "mmrf-witness-descriptor-0.6",
        "witness_id": witness_id,
        "public_ed25519": raw_ed25519_public(private.public_key()),
        "created_at": utc_now(),
    }
    descriptor["descriptor_sha256"] = sha256_json(descriptor)
    public_dir.mkdir(parents=True, exist_ok=True)
    descriptor_path = public_dir / f"{witness_id}.descriptor.json"
    descriptor_path.write_text(
        json.dumps(descriptor, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "private_key_path": str(private_path),
        "descriptor_path": str(descriptor_path),
        "descriptor": descriptor,
    }


class Witness:
    def __init__(
        self,
        *,
        descriptor: Mapping[str, Any],
        private_key_path: Path,
        state_db: Path,
        log_public_key_path: Path,
    ):
        self.descriptor = dict(descriptor)
        self.private_key_path = Path(private_key_path)
        self.state_db = Path(state_db)
        self.log_public_key_path = Path(log_public_key_path)
        self.state_db.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.state_db)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS observed_heads(
                log_id TEXT PRIMARY KEY,
                tree_size INTEGER NOT NULL,
                root_hash_sha256 TEXT NOT NULL,
                sth_sha256 TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def cosign(
        self,
        sth: Mapping[str, Any],
        entries: Sequence[Mapping[str, Any]],
    ) -> dict:
        if not verify_sth_signature(sth, self.log_public_key_path):
            return {"accepted": False, "reason": "log_signature_invalid"}
        if int(sth["tree_size"]) != len(entries):
            return {"accepted": False, "reason": "tree_size_mismatch"}
        computed_root = merkle_root(entries)
        if computed_root != sth["root_hash_sha256"]:
            return {"accepted": False, "reason": "root_mismatch"}

        prior = self.conn.execute(
            "SELECT * FROM observed_heads WHERE log_id = ?",
            (sth["log_id"],),
        ).fetchone()
        if prior:
            if int(sth["tree_size"]) < int(prior["tree_size"]):
                return {"accepted": False, "reason": "tree_size_rollback"}
            if int(sth["tree_size"]) == int(prior["tree_size"]):
                if sth["root_hash_sha256"] != prior["root_hash_sha256"]:
                    return {"accepted": False, "reason": "equivocation_detected"}
            elif sth["previous_sth_sha256"] != prior["sth_sha256"]:
                return {"accepted": False, "reason": "sth_chain_mismatch"}

        signature = b64(
            load_ed25519_private(self.private_key_path).sign(
                sth["sth_sha256"].encode("ascii")
            )
        )
        self.conn.execute(
            """
            INSERT OR REPLACE INTO observed_heads(
                log_id, tree_size, root_hash_sha256,
                sth_sha256, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                sth["log_id"],
                sth["tree_size"],
                sth["root_hash_sha256"],
                sth["sth_sha256"],
                utc_now(),
            ),
        )
        self.conn.commit()
        return {
            "accepted": True,
            "witness_id": self.descriptor["witness_id"],
            "witness_descriptor_sha256": self.descriptor[
                "descriptor_sha256"
            ],
            "sth_sha256": sth["sth_sha256"],
            "signature_ed25519": signature,
        }


def verify_witness_quorum(
    *,
    sth: Mapping[str, Any],
    signatures: Sequence[Mapping[str, Any]],
    witness_descriptors: Mapping[str, Mapping[str, Any]],
    threshold: int,
) -> dict:
    valid_ids: set[str] = set()
    failures: list[dict] = []
    for item in signatures:
        witness_id = item.get("witness_id")
        descriptor = witness_descriptors.get(str(witness_id))
        if descriptor is None:
            failures.append({"witness_id": witness_id, "reason": "unknown"})
            continue
        if item.get("sth_sha256") != sth.get("sth_sha256"):
            failures.append({
                "witness_id": witness_id,
                "reason": "sth_binding_mismatch",
            })
            continue
        try:
            load_ed25519_public(
                descriptor["public_ed25519"]
            ).verify(
                unb64(item["signature_ed25519"]),
                sth["sth_sha256"].encode("ascii"),
            )
            valid_ids.add(str(witness_id))
        except Exception as exc:
            failures.append({
                "witness_id": witness_id,
                "reason": f"signature_invalid:{type(exc).__name__}",
            })
    return {
        "valid": len(valid_ids) >= int(threshold),
        "threshold": int(threshold),
        "valid_witnesses": sorted(valid_ids),
        "valid_count": len(valid_ids),
        "failures": failures,
    }


def derive_trust_state(entries: Sequence[Mapping[str, Any]]) -> dict:
    nodes: dict[str, dict] = {}
    for entry in entries:
        event_type = entry["entry_type"]
        payload = entry["payload"]
        node_id = entry["subject_id"]
        if event_type == "NODE_REGISTER":
            descriptor = payload["descriptor"]
            if not verify_epoch_descriptor(descriptor):
                raise ValueError("invalid registered descriptor")
            if node_id in nodes:
                raise ValueError("duplicate node registration")
            nodes[node_id] = {
                "status": "ACTIVE",
                "descriptor": descriptor,
                "history": [descriptor["descriptor_sha256"]],
            }
        elif event_type == "NODE_ROTATE":
            state = nodes[node_id]
            descriptor = payload["new_descriptor"]
            if not verify_descriptor_continuity(
                descriptor,
                state["descriptor"],
                payload["continuity_signature_ed25519"],
            ):
                raise ValueError("rotation continuity invalid")
            state["descriptor"] = descriptor
            state["status"] = "ACTIVE"
            state["history"].append(descriptor["descriptor_sha256"])
        elif event_type == "NODE_REVOKE":
            state = nodes[node_id]
            state["status"] = "REVOKED"
            state["revocation_reason"] = payload["reason"]
        elif event_type == "NODE_RECOVER":
            state = nodes[node_id]
            descriptor = payload["new_descriptor"]
            if not verify_epoch_descriptor(descriptor):
                raise ValueError("recovery descriptor invalid")
            if int(descriptor["key_epoch"]) <= int(
                state["descriptor"]["key_epoch"]
            ):
                raise ValueError("recovery epoch must advance")
            if not payload.get("threshold_recovery_completed"):
                raise ValueError("recovery threshold evidence absent")
            state["descriptor"] = descriptor
            state["status"] = "ACTIVE"
            state["history"].append(descriptor["descriptor_sha256"])
            state["recovery_manifest_sha256"] = payload[
                "recovery_manifest_sha256"
            ]
    return {"nodes": nodes}


def node_authorized(
    trust_state: Mapping[str, Any],
    descriptor: Mapping[str, Any],
) -> dict:
    state = trust_state.get("nodes", {}).get(descriptor.get("node_id"))
    if state is None:
        return {"authorized": False, "reason": "node_not_registered"}
    if state["status"] != "ACTIVE":
        return {"authorized": False, "reason": "node_revoked"}
    if (
        state["descriptor"]["descriptor_sha256"]
        != descriptor.get("descriptor_sha256")
    ):
        return {"authorized": False, "reason": "descriptor_not_current"}
    return {"authorized": True, "reason": None}


def _stable_object_meta(
    *,
    object_id: str,
    object_type: str,
    classification: str,
    payload_origin_node_id: str,
    payload_origin_descriptor_sha256: str,
    created_at: str,
) -> dict:
    return {
        "schema": "mmrf-encrypted-object-0.6",
        "object_id": object_id,
        "object_type": object_type,
        "classification": classification,
        "payload_origin_node_id": payload_origin_node_id,
        "payload_origin_descriptor_sha256": (
            payload_origin_descriptor_sha256
        ),
        "created_at": created_at,
        "payload_algorithm": "A256GCM",
        "aad_profile": "MMRF-STABLE-AAD-0.6",
    }


def _wrap_dek(
    dek: bytes,
    descriptor: Mapping[str, Any],
    aad: bytes,
) -> dict:
    ephemeral_private = x25519.X25519PrivateKey.generate()
    recipient = load_x25519_public(
        descriptor["encryption_public_x25519"]
    )
    shared = ephemeral_private.exchange(recipient)
    salt = os.urandom(16)
    kek = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=b"MMRF-DEK-WRAP-v0.6",
    ).derive(shared)
    nonce = os.urandom(12)
    wrapped = AESGCM(kek).encrypt(nonce, dek, aad)
    return {
        "recipient_node_id": descriptor["node_id"],
        "recipient_key_epoch": descriptor["key_epoch"],
        "recipient_descriptor_sha256": descriptor["descriptor_sha256"],
        "algorithm": "X25519-HKDF-SHA256+A256GCM",
        "ephemeral_public_x25519": raw_x25519_public(
            ephemeral_private.public_key()
        ),
        "hkdf_salt": b64(salt),
        "nonce": b64(nonce),
        "wrapped_dek": b64(wrapped),
    }


def _unwrap_dek(
    wrap: Mapping[str, Any],
    private_key_path: Path,
    aad: bytes,
) -> bytes:
    private = load_x25519_private(private_key_path)
    ephemeral = load_x25519_public(
        wrap["ephemeral_public_x25519"]
    )
    shared = private.exchange(ephemeral)
    kek = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=unb64(wrap["hkdf_salt"]),
        info=b"MMRF-DEK-WRAP-v0.6",
    ).derive(shared)
    return AESGCM(kek).decrypt(
        unb64(wrap["nonce"]),
        unb64(wrap["wrapped_dek"]),
        aad,
    )


def _sign_envelope(
    core: Mapping[str, Any],
    signer_descriptor: Mapping[str, Any],
    signer_identity_private_path: Path,
) -> dict:
    signed = {
        **dict(core),
        "signer_node_id": signer_descriptor["node_id"],
        "signer_key_epoch": signer_descriptor["key_epoch"],
        "signer_descriptor_sha256": signer_descriptor[
            "descriptor_sha256"
        ],
    }
    cid = "mmrf-cid:" + sha256_json(signed)
    signed_with_cid = {**signed, "cid": cid}
    signature = b64(
        load_ed25519_private(
            signer_identity_private_path
        ).sign(canonical_json(signed_with_cid).encode("utf-8"))
    )
    return {
        **signed_with_cid,
        "signer_signature_ed25519": signature,
    }


def encrypt_object_v06(
    *,
    payload: Mapping[str, Any],
    object_id: str,
    object_type: str,
    classification: str,
    origin_descriptor: Mapping[str, Any],
    origin_identity_private_path: Path,
    recipient_descriptors: Sequence[Mapping[str, Any]],
) -> dict:
    if classification not in {"L2_CONTROLLED", "L3_VAULT"}:
        raise ValueError("invalid vault classification")
    recipients = {
        descriptor["node_id"]: descriptor
        for descriptor in recipient_descriptors
    }
    recipients[origin_descriptor["node_id"]] = origin_descriptor
    meta = _stable_object_meta(
        object_id=object_id,
        object_type=object_type,
        classification=classification,
        payload_origin_node_id=origin_descriptor["node_id"],
        payload_origin_descriptor_sha256=origin_descriptor[
            "descriptor_sha256"
        ],
        created_at=utc_now(),
    )
    aad = canonical_json(meta).encode("utf-8")
    payload_bytes = canonical_json(payload).encode("utf-8")
    sealed = canonical_json({
        "payload": dict(payload),
        "payload_sha256": sha256_bytes(payload_bytes),
    }).encode("utf-8")
    dek = os.urandom(32)
    nonce = os.urandom(12)
    ciphertext = AESGCM(dek).encrypt(nonce, sealed, aad)
    core = {
        **meta,
        "payload_nonce": b64(nonce),
        "ciphertext": b64(ciphertext),
        "ciphertext_sha256": sha256_bytes(ciphertext),
        "dek_wraps": [
            _wrap_dek(dek, recipients[node_id], aad)
            for node_id in sorted(recipients)
        ],
        "recipient_node_ids": sorted(recipients),
        "rewrap_generation": 0,
        "predecessor_cid": None,
        "rewrap_reason": "INITIAL_ENCRYPTION",
    }
    return _sign_envelope(
        core,
        origin_descriptor,
        origin_identity_private_path,
    )


def verify_object_v06(
    envelope: Mapping[str, Any],
    descriptors_by_hash: Mapping[str, Mapping[str, Any]],
) -> dict:
    try:
        descriptor = descriptors_by_hash[
            envelope["signer_descriptor_sha256"]
        ]
        signed = {
            key: value
            for key, value in envelope.items()
            if key != "signer_signature_ed25519"
        }
        load_ed25519_public(
            descriptor["identity_public_ed25519"]
        ).verify(
            unb64(envelope["signer_signature_ed25519"]),
            canonical_json(signed).encode("utf-8"),
        )
        unsigned = {
            key: value
            for key, value in signed.items()
            if key != "cid"
        }
        cid_ok = envelope["cid"] == "mmrf-cid:" + sha256_json(unsigned)
        cipher = unb64(envelope["ciphertext"])
        cipher_ok = (
            envelope["ciphertext_sha256"]
            == sha256_bytes(cipher)
        )
        wrap_nodes = sorted(
            wrap["recipient_node_id"]
            for wrap in envelope["dek_wraps"]
        )
        recipients_ok = wrap_nodes == sorted(
            envelope["recipient_node_ids"]
        )
        descriptor_ok = (
            envelope["signer_node_id"] == descriptor["node_id"]
            and int(envelope["signer_key_epoch"])
            == int(descriptor["key_epoch"])
        )
        valid = cid_ok and cipher_ok and recipients_ok and descriptor_ok
        return {
            "valid": valid,
            "cid_ok": cid_ok,
            "ciphertext_hash_ok": cipher_ok,
            "recipients_ok": recipients_ok,
            "signer_descriptor_ok": descriptor_ok,
            "reason": None if valid else "integrity_mismatch",
        }
    except Exception as exc:
        return {
            "valid": False,
            "reason": f"verification_error:{type(exc).__name__}",
        }


def decrypt_object_v06(
    *,
    envelope: Mapping[str, Any],
    node_descriptor: Mapping[str, Any],
    node_encryption_private_path: Path,
    descriptors_by_hash: Mapping[str, Mapping[str, Any]],
) -> dict:
    check = verify_object_v06(envelope, descriptors_by_hash)
    if not check["valid"]:
        raise ValueError(check)
    meta = _stable_object_meta(
        object_id=envelope["object_id"],
        object_type=envelope["object_type"],
        classification=envelope["classification"],
        payload_origin_node_id=envelope["payload_origin_node_id"],
        payload_origin_descriptor_sha256=envelope[
            "payload_origin_descriptor_sha256"
        ],
        created_at=envelope["created_at"],
    )
    aad = canonical_json(meta).encode("utf-8")
    wrap = next(
        (
            item
            for item in envelope["dek_wraps"]
            if item["recipient_node_id"] == node_descriptor["node_id"]
            and int(item["recipient_key_epoch"])
            == int(node_descriptor["key_epoch"])
            and item["recipient_descriptor_sha256"]
            == node_descriptor["descriptor_sha256"]
        ),
        None,
    )
    if wrap is None:
        raise PermissionError("current node epoch is not a recipient")
    dek = _unwrap_dek(wrap, node_encryption_private_path, aad)
    sealed = AESGCM(dek).decrypt(
        unb64(envelope["payload_nonce"]),
        unb64(envelope["ciphertext"]),
        aad,
    )
    document = json.loads(sealed)
    if document["payload_sha256"] != sha256_bytes(
        canonical_json(document["payload"]).encode("utf-8")
    ):
        raise ValueError("payload hash mismatch")
    return document["payload"]


def rewrap_object_v06(
    *,
    envelope: Mapping[str, Any],
    authorizing_descriptor: Mapping[str, Any],
    authorizing_encryption_private_path: Path,
    new_recipient_descriptors: Sequence[Mapping[str, Any]],
    remove_node_ids: Sequence[str],
    signer_descriptor: Mapping[str, Any],
    signer_identity_private_path: Path,
    reason: str,
    descriptors_by_hash: Mapping[str, Mapping[str, Any]],
) -> dict:
    check = verify_object_v06(envelope, descriptors_by_hash)
    if not check["valid"]:
        raise ValueError(check)
    meta = _stable_object_meta(
        object_id=envelope["object_id"],
        object_type=envelope["object_type"],
        classification=envelope["classification"],
        payload_origin_node_id=envelope["payload_origin_node_id"],
        payload_origin_descriptor_sha256=envelope[
            "payload_origin_descriptor_sha256"
        ],
        created_at=envelope["created_at"],
    )
    aad = canonical_json(meta).encode("utf-8")
    source_wrap = next(
        (
            item
            for item in envelope["dek_wraps"]
            if item["recipient_node_id"]
            == authorizing_descriptor["node_id"]
            and int(item["recipient_key_epoch"])
            == int(authorizing_descriptor["key_epoch"])
            and item["recipient_descriptor_sha256"]
            == authorizing_descriptor["descriptor_sha256"]
        ),
        None,
    )
    if source_wrap is None:
        raise PermissionError("authorizing node has no valid DEK wrap")
    dek = _unwrap_dek(
        source_wrap,
        authorizing_encryption_private_path,
        aad,
    )

    removed = set(remove_node_ids)
    retained: dict[str, dict] = {}
    for item in envelope["dek_wraps"]:
        if item["recipient_node_id"] not in removed:
            retained[item["recipient_node_id"]] = dict(item)
    for descriptor in new_recipient_descriptors:
        retained[descriptor["node_id"]] = _wrap_dek(
            dek, descriptor, aad
        )

    core = {
        **meta,
        "payload_nonce": envelope["payload_nonce"],
        "ciphertext": envelope["ciphertext"],
        "ciphertext_sha256": envelope["ciphertext_sha256"],
        "dek_wraps": [
            retained[node_id]
            for node_id in sorted(retained)
        ],
        "recipient_node_ids": sorted(retained),
        "rewrap_generation": int(
            envelope.get("rewrap_generation", 0)
        ) + 1,
        "predecessor_cid": envelope["cid"],
        "rewrap_reason": reason,
    }
    return _sign_envelope(
        core,
        signer_descriptor,
        signer_identity_private_path,
    )


def split_secret(
    secret: bytes,
    *,
    threshold: int,
    share_count: int,
    package_id: str,
) -> list[dict]:
    if not (2 <= threshold <= share_count):
        raise ValueError("invalid threshold")
    secret_int = int.from_bytes(secret, "big")
    if secret_int >= SHAMIR_PRIME:
        raise ValueError("secret too large")
    coefficients = [secret_int] + [
        int.from_bytes(os.urandom(64), "big") % SHAMIR_PRIME
        for _ in range(threshold - 1)
    ]
    shares = []
    for x in range(1, share_count + 1):
        y = sum(
            coefficient * pow(x, degree, SHAMIR_PRIME)
            for degree, coefficient in enumerate(coefficients)
        ) % SHAMIR_PRIME
        core = {
            "schema": "mmrf-recovery-share-0.6",
            "package_id": package_id,
            "x": x,
            "y_hex": format(y, "x"),
            "threshold": threshold,
            "share_count": share_count,
        }
        shares.append({
            **core,
            "share_sha256": sha256_json(core),
        })
    return shares


def reconstruct_secret(
    shares: Sequence[Mapping[str, Any]],
    *,
    expected_share_hashes: Mapping[int, str],
    threshold: int,
    secret_length: int,
) -> bytes:
    if len(shares) < threshold:
        raise ValueError("insufficient_shares")
    selected = list(shares)[:threshold]
    for share in selected:
        x = int(share["x"])
        core = {
            key: value
            for key, value in share.items()
            if key != "share_sha256"
        }
        if sha256_json(core) != share.get("share_sha256"):
            raise ValueError("share_self_hash_mismatch")
        if expected_share_hashes.get(x) != share["share_sha256"]:
            raise ValueError("share_manifest_hash_mismatch")

    secret_int = 0
    points = [
        (int(share["x"]), int(share["y_hex"], 16))
        for share in selected
    ]
    for index, (x_i, y_i) in enumerate(points):
        numerator = 1
        denominator = 1
        for other_index, (x_j, _) in enumerate(points):
            if index == other_index:
                continue
            numerator = (
                numerator * (-x_j)
            ) % SHAMIR_PRIME
            denominator = (
                denominator * (x_i - x_j)
            ) % SHAMIR_PRIME
        lagrange = numerator * pow(
            denominator, SHAMIR_PRIME - 2, SHAMIR_PRIME
        ) % SHAMIR_PRIME
        secret_int = (
            secret_int + y_i * lagrange
        ) % SHAMIR_PRIME
    return secret_int.to_bytes(secret_length, "big")


def create_recovery_escrow(
    *,
    node_id: str,
    key_epoch: int,
    encryption_private_key_path: Path,
    threshold: int = 3,
    share_count: int = 5,
) -> tuple[dict, list[dict]]:
    package_id = f"recovery:{node_id}:epoch{key_epoch}:{uuid.uuid4()}"
    secret = os.urandom(32)
    private_pem = Path(encryption_private_key_path).read_bytes()
    aad_core = {
        "schema": "mmrf-recovery-escrow-0.6",
        "package_id": package_id,
        "node_id": node_id,
        "key_epoch": key_epoch,
        "threshold": threshold,
        "share_count": share_count,
        "private_key_type": "X25519_PKCS8_PEM",
        "created_at": utc_now(),
    }
    nonce = os.urandom(12)
    encrypted = AESGCM(secret).encrypt(
        nonce,
        private_pem,
        canonical_json(aad_core).encode("utf-8"),
    )
    shares = split_secret(
        secret,
        threshold=threshold,
        share_count=share_count,
        package_id=package_id,
    )
    manifest = {
        **aad_core,
        "nonce": b64(nonce),
        "encrypted_private_key": b64(encrypted),
        "encrypted_private_key_sha256": sha256_bytes(encrypted),
        "share_hashes": {
            str(share["x"]): share["share_sha256"]
            for share in shares
        },
    }
    manifest["manifest_sha256"] = sha256_json(manifest)
    return manifest, shares


def recover_private_key_from_escrow(
    *,
    manifest: Mapping[str, Any],
    shares: Sequence[Mapping[str, Any]],
) -> bytes:
    if manifest.get("manifest_sha256") != sha256_json({
        key: value
        for key, value in manifest.items()
        if key != "manifest_sha256"
    }):
        raise ValueError("recovery_manifest_hash_mismatch")
    secret = reconstruct_secret(
        shares,
        expected_share_hashes={
            int(key): value
            for key, value in manifest["share_hashes"].items()
        },
        threshold=int(manifest["threshold"]),
        secret_length=32,
    )
    aad_core = {
        key: manifest[key]
        for key in (
            "schema",
            "package_id",
            "node_id",
            "key_epoch",
            "threshold",
            "share_count",
            "private_key_type",
            "created_at",
        )
    }
    encrypted = unb64(manifest["encrypted_private_key"])
    if sha256_bytes(encrypted) != manifest[
        "encrypted_private_key_sha256"
    ]:
        raise ValueError("encrypted_backup_hash_mismatch")
    return AESGCM(secret).decrypt(
        unb64(manifest["nonce"]),
        encrypted,
        canonical_json(aad_core).encode("utf-8"),
    )


class ObjectStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS objects(
                cid TEXT PRIMARY KEY,
                object_id TEXT NOT NULL,
                predecessor_cid TEXT,
                rewrap_generation INTEGER NOT NULL,
                ciphertext_sha256 TEXT NOT NULL,
                active INTEGER NOT NULL,
                envelope_json TEXT NOT NULL,
                stored_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def store(self, envelope: Mapping[str, Any]) -> None:
        predecessor = envelope.get("predecessor_cid")
        if predecessor:
            self.conn.execute(
                "UPDATE objects SET active = 0 WHERE cid = ?",
                (predecessor,),
            )
        self.conn.execute(
            """
            INSERT INTO objects(
                cid, object_id, predecessor_cid,
                rewrap_generation, ciphertext_sha256,
                active, envelope_json, stored_at
            ) VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                envelope["cid"],
                envelope["object_id"],
                predecessor,
                envelope["rewrap_generation"],
                envelope["ciphertext_sha256"],
                canonical_json(envelope),
                utc_now(),
            ),
        )
        self.conn.commit()

    def active_envelopes(self) -> list[dict]:
        return [
            json.loads(row["envelope_json"])
            for row in self.conn.execute(
                "SELECT envelope_json FROM objects WHERE active = 1 ORDER BY object_id"
            )
        ]

    def stats(self) -> dict:
        return {
            "all_versions": self.conn.execute(
                "SELECT COUNT(*) AS n FROM objects"
            ).fetchone()["n"],
            "active_objects": self.conn.execute(
                "SELECT COUNT(*) AS n FROM objects WHERE active = 1"
            ).fetchone()["n"],
            "max_rewrap_generation": self.conn.execute(
                "SELECT COALESCE(MAX(rewrap_generation),0) AS n FROM objects"
            ).fetchone()["n"],
        }
