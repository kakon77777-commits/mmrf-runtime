from __future__ import annotations

import base64
import hashlib
import json
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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def unix_now() -> int:
    return int(time.time())


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def raw_ed25519_public(key: ed25519.Ed25519PublicKey) -> str:
    return b64(key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))


def raw_x25519_public(key: x25519.X25519PublicKey) -> str:
    return b64(key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))


def load_ed25519_public(raw: str) -> ed25519.Ed25519PublicKey:
    return ed25519.Ed25519PublicKey.from_public_bytes(unb64(raw))


def load_x25519_public(raw: str) -> x25519.X25519PublicKey:
    return x25519.X25519PublicKey.from_public_bytes(unb64(raw))


def save_private_key(key: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    os.chmod(path, 0o600)


def load_ed25519_private(path: Path) -> ed25519.Ed25519PrivateKey:
    key = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    if not isinstance(key, ed25519.Ed25519PrivateKey):
        raise TypeError("not an Ed25519 private key")
    return key


def load_x25519_private(path: Path) -> x25519.X25519PrivateKey:
    key = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    if not isinstance(key, x25519.X25519PrivateKey):
        raise TypeError("not an X25519 private key")
    return key


def generate_node_material(
    *, node_id: str, private_dir: Path, public_dir: Path,
    roles: Sequence[str], accepted_measurements: Sequence[str],
) -> dict:
    identity_private = ed25519.Ed25519PrivateKey.generate()
    encryption_private = x25519.X25519PrivateKey.generate()
    identity_path = private_dir / f"{node_id}.identity.private.pem"
    encryption_path = private_dir / f"{node_id}.encryption.private.pem"
    save_private_key(identity_private, identity_path)
    save_private_key(encryption_private, encryption_path)

    descriptor_core = {
        "schema": "mmrf-node-descriptor-0.5",
        "node_id": node_id,
        "roles": sorted(set(roles)),
        "identity_public_ed25519": raw_ed25519_public(identity_private.public_key()),
        "encryption_public_x25519": raw_x25519_public(encryption_private.public_key()),
        "accepted_measurements": sorted(set(accepted_measurements)),
        "created_at": utc_now(),
    }
    descriptor = {**descriptor_core, "descriptor_sha256": sha256_json(descriptor_core)}
    public_dir.mkdir(parents=True, exist_ok=True)
    descriptor_path = public_dir / f"{node_id}.descriptor.json"
    descriptor_path.write_text(json.dumps(descriptor, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "node_id": node_id,
        "identity_private_path": str(identity_path),
        "encryption_private_path": str(encryption_path),
        "descriptor_path": str(descriptor_path),
        "descriptor": descriptor,
    }


def verify_descriptor(descriptor: Mapping[str, Any]) -> bool:
    core = {k: v for k, v in descriptor.items() if k != "descriptor_sha256"}
    return (
        descriptor.get("schema") == "mmrf-node-descriptor-0.5"
        and descriptor.get("descriptor_sha256") == sha256_json(core)
    )


def issue_attestation(
    *, node_id: str, descriptor: Mapping[str, Any], identity_private_path: Path,
    measurement_sha256: str, config_sha256: str, ttl_seconds: int = 600,
) -> dict:
    if node_id != descriptor["node_id"] or not verify_descriptor(descriptor):
        raise ValueError("descriptor mismatch")
    now = unix_now()
    claims = {
        "schema": "mmrf-software-attestation-0.5",
        "node_id": node_id,
        "descriptor_sha256": descriptor["descriptor_sha256"],
        "measurement_sha256": measurement_sha256,
        "config_sha256": config_sha256,
        "boot_nonce": uuid.uuid4().hex,
        "issued_at": now,
        "expires_at": now + int(ttl_seconds),
        "attestation_type": "SOFTWARE_SIGNED_PROTOTYPE",
    }
    signature = load_ed25519_private(identity_private_path).sign(
        canonical_json(claims).encode("utf-8")
    )
    return {"claims": claims, "signature_ed25519": b64(signature)}


def verify_attestation(
    attestation: Mapping[str, Any], descriptor: Mapping[str, Any], *, now: Optional[int] = None,
) -> dict:
    now = unix_now() if now is None else int(now)
    try:
        claims = dict(attestation["claims"])
        load_ed25519_public(descriptor["identity_public_ed25519"]).verify(
            unb64(attestation["signature_ed25519"]), canonical_json(claims).encode("utf-8")
        )
    except Exception as exc:
        return {"valid": False, "reason": f"signature_invalid:{type(exc).__name__}"}
    checks = {
        "descriptor_valid": verify_descriptor(descriptor),
        "node_id_ok": claims.get("node_id") == descriptor.get("node_id"),
        "descriptor_hash_ok": claims.get("descriptor_sha256") == descriptor.get("descriptor_sha256"),
        "measurement_allowed": claims.get("measurement_sha256") in set(descriptor.get("accepted_measurements", [])),
        "time_ok": int(claims.get("issued_at", 0)) <= now <= int(claims.get("expires_at", 0)),
        "prototype_declared": claims.get("attestation_type") == "SOFTWARE_SIGNED_PROTOTYPE",
    }
    return {"valid": all(checks.values()), "checks": checks, "claims": claims,
            "reason": None if all(checks.values()) else "claim_mismatch"}


class KeyUnwrapProvider:
    adapter_name = "ABSTRACT"
    def unwrap_dek(self, wrap: Mapping[str, Any], *, aad: bytes) -> bytes:
        raise NotImplementedError


class LocalX25519KMS(KeyUnwrapProvider):
    adapter_name = "LOCAL_X25519_KMS_PROTOTYPE"
    def __init__(self, node_id: str, private_key_path: Path):
        self.node_id = node_id
        self.private_key_path = Path(private_key_path)
    def unwrap_dek(self, wrap: Mapping[str, Any], *, aad: bytes) -> bytes:
        if wrap.get("recipient_node_id") != self.node_id:
            raise PermissionError("DEK wrap is not addressed to this node")
        private = load_x25519_private(self.private_key_path)
        ephemeral = load_x25519_public(wrap["ephemeral_public_x25519"])
        shared = private.exchange(ephemeral)
        kek = HKDF(algorithm=hashes.SHA256(), length=32, salt=unb64(wrap["hkdf_salt"]),
                   info=b"MMRF-DEK-WRAP-v0.5").derive(shared)
        return AESGCM(kek).decrypt(unb64(wrap["nonce"]), unb64(wrap["wrapped_dek"]), aad)


class PKCS11HSMAdapter(KeyUnwrapProvider):
    adapter_name = "PKCS11_HSM_INTERFACE_STUB"
    def __init__(self, key_label: str): self.key_label = key_label
    def unwrap_dek(self, wrap: Mapping[str, Any], *, aad: bytes) -> bytes:
        raise NotImplementedError("Bind this adapter to an HSM/PKCS#11 provider in production")


def wrap_dek_for_recipient(dek: bytes, descriptor: Mapping[str, Any], *, aad: bytes) -> dict:
    ephemeral_private = x25519.X25519PrivateKey.generate()
    shared = ephemeral_private.exchange(load_x25519_public(descriptor["encryption_public_x25519"]))
    salt = os.urandom(16)
    kek = HKDF(algorithm=hashes.SHA256(), length=32, salt=salt,
               info=b"MMRF-DEK-WRAP-v0.5").derive(shared)
    nonce = os.urandom(12)
    wrapped = AESGCM(kek).encrypt(nonce, dek, aad)
    return {
        "recipient_node_id": descriptor["node_id"],
        "recipient_descriptor_sha256": descriptor["descriptor_sha256"],
        "algorithm": "X25519-HKDF-SHA256+A256GCM",
        "ephemeral_public_x25519": raw_x25519_public(ephemeral_private.public_key()),
        "hkdf_salt": b64(salt),
        "nonce": b64(nonce),
        "wrapped_dek": b64(wrapped),
    }


def encrypt_object(
    *, payload: Mapping[str, Any], object_id: str, object_type: str, classification: str,
    origin_descriptor: Mapping[str, Any], origin_identity_private_path: Path,
    recipient_descriptors: Sequence[Mapping[str, Any]],
) -> dict:
    if classification not in {"L2_CONTROLLED", "L3_VAULT"}:
        raise ValueError("federated vault stores only L2/L3 objects")
    if not verify_descriptor(origin_descriptor):
        raise ValueError("invalid origin descriptor")
    recipients = {item["node_id"]: item for item in recipient_descriptors}
    recipients[origin_descriptor["node_id"]] = origin_descriptor
    meta = {
        "schema": "mmrf-encrypted-object-0.5",
        "object_id": object_id,
        "object_type": object_type,
        "classification": classification,
        "origin_node_id": origin_descriptor["node_id"],
        "origin_descriptor_sha256": origin_descriptor["descriptor_sha256"],
        "created_at": utc_now(),
        "payload_algorithm": "A256GCM",
        "recipient_node_ids": sorted(recipients),
    }
    aad = canonical_json(meta).encode("utf-8")
    payload_bytes = canonical_json(payload).encode("utf-8")
    sealed = canonical_json({"payload": payload, "payload_sha256": sha256_bytes(payload_bytes)}).encode("utf-8")
    dek = os.urandom(32)
    nonce = os.urandom(12)
    ciphertext = AESGCM(dek).encrypt(nonce, sealed, aad)
    wraps = [wrap_dek_for_recipient(dek, recipients[node_id], aad=aad) for node_id in sorted(recipients)]
    core = {
        **meta,
        "payload_nonce": b64(nonce),
        "ciphertext": b64(ciphertext),
        "ciphertext_sha256": sha256_bytes(ciphertext),
        "dek_wraps": wraps,
    }
    cid = "mmrf-cid:" + sha256_json(core)
    signed = {**core, "cid": cid}
    signature = load_ed25519_private(origin_identity_private_path).sign(
        canonical_json(signed).encode("utf-8")
    )
    return {**signed, "origin_signature_ed25519": b64(signature)}


def verify_encrypted_object(envelope: Mapping[str, Any], trusted_descriptors: Mapping[str, Mapping[str, Any]]) -> dict:
    try:
        origin = envelope["origin_node_id"]
        descriptor = trusted_descriptors[origin]
        signature = envelope["origin_signature_ed25519"]
        signed = {k: v for k, v in envelope.items() if k != "origin_signature_ed25519"}
        load_ed25519_public(descriptor["identity_public_ed25519"]).verify(
            unb64(signature), canonical_json(signed).encode("utf-8")
        )
        core = {k: v for k, v in signed.items() if k != "cid"}
        cid_ok = envelope["cid"] == "mmrf-cid:" + sha256_json(core)
        ciphertext = unb64(envelope["ciphertext"])
        cipher_hash_ok = envelope["ciphertext_sha256"] == sha256_bytes(ciphertext)
        descriptor_ok = envelope["origin_descriptor_sha256"] == descriptor["descriptor_sha256"]
        wraps_ok = all(w["recipient_node_id"] in envelope["recipient_node_ids"] for w in envelope["dek_wraps"])
        valid = cid_ok and cipher_hash_ok and descriptor_ok and wraps_ok
        return {"valid": valid, "cid_ok": cid_ok, "ciphertext_hash_ok": cipher_hash_ok,
                "descriptor_ok": descriptor_ok, "wraps_ok": wraps_ok,
                "reason": None if valid else "integrity_mismatch"}
    except Exception as exc:
        return {"valid": False, "reason": f"verification_error:{type(exc).__name__}"}


def decrypt_object(
    envelope: Mapping[str, Any], *, node_id: str, kms: KeyUnwrapProvider,
    trusted_descriptors: Mapping[str, Mapping[str, Any]],
) -> dict:
    verification = verify_encrypted_object(envelope, trusted_descriptors)
    if not verification["valid"]:
        raise ValueError(f"encrypted object invalid: {verification}")
    meta_keys = ["schema","object_id","object_type","classification","origin_node_id",
                 "origin_descriptor_sha256","created_at","payload_algorithm","recipient_node_ids"]
    meta = {key: envelope[key] for key in meta_keys}
    aad = canonical_json(meta).encode("utf-8")
    wrap = next((w for w in envelope["dek_wraps"] if w["recipient_node_id"] == node_id), None)
    if wrap is None:
        raise PermissionError("node is not an authorized recipient")
    dek = kms.unwrap_dek(wrap, aad=aad)
    sealed = AESGCM(dek).decrypt(unb64(envelope["payload_nonce"]), unb64(envelope["ciphertext"]), aad)
    document = json.loads(sealed)
    payload_bytes = canonical_json(document["payload"]).encode("utf-8")
    if document["payload_sha256"] != sha256_bytes(payload_bytes):
        raise ValueError("decrypted payload hash mismatch")
    return document["payload"]


class VaultNode:
    def __init__(
        self, *, node_id: str, db_path: Path, descriptor: Mapping[str, Any],
        identity_private_path: Optional[Path], kms: Optional[KeyUnwrapProvider],
        trusted_descriptors: Mapping[str, Mapping[str, Any]],
    ):
        self.node_id=node_id; self.db_path=Path(db_path); self.descriptor=dict(descriptor)
        self.identity_private_path=Path(identity_private_path) if identity_private_path else None
        self.kms=kms; self.trusted_descriptors={k:dict(v) for k,v in trusted_descriptors.items()}
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn=sqlite3.connect(self.db_path); self.conn.row_factory=sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL"); self.conn.execute("PRAGMA synchronous=FULL")
    def close(self): self.conn.close()
    def init_schema(self):
        self.conn.executescript('''
        CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS objects(cid TEXT PRIMARY KEY,object_id TEXT NOT NULL,origin_node_id TEXT NOT NULL,
          classification TEXT NOT NULL,envelope_json TEXT NOT NULL,envelope_sha256 TEXT NOT NULL,received_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS local_audit(sequence INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT UNIQUE NOT NULL,
          previous_hash_sha256 TEXT NOT NULL,event_hash_sha256 TEXT UNIQUE NOT NULL,event_type TEXT NOT NULL,
          object_cid TEXT,detail_json TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS checkpoints(checkpoint_sequence INTEGER PRIMARY KEY,checkpoint_id TEXT UNIQUE NOT NULL,
          previous_checkpoint_sha256 TEXT NOT NULL,audit_sequence INTEGER NOT NULL,audit_root_sha256 TEXT NOT NULL,
          attestation_sha256 TEXT NOT NULL,checkpoint_hash_sha256 TEXT UNIQUE NOT NULL,checkpoint_json TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS peer_state(peer_node_id TEXT PRIMARY KEY,checkpoint_sequence INTEGER NOT NULL,
          checkpoint_hash_sha256 TEXT NOT NULL,audit_sequence INTEGER NOT NULL,audit_root_sha256 TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS replication_receipts(bundle_id TEXT PRIMARY KEY,origin_node_id TEXT NOT NULL,status TEXT NOT NULL,
          detail_json TEXT NOT NULL,created_at TEXT NOT NULL);
        ''')
        self.conn.execute("INSERT OR REPLACE INTO metadata VALUES('node_descriptor',?)", (canonical_json(self.descriptor),))
        self.conn.commit()
    def _audit_root(self):
        row=self.conn.execute("SELECT event_hash_sha256 FROM local_audit ORDER BY sequence DESC LIMIT 1").fetchone()
        return row['event_hash_sha256'] if row else '0'*64
    def _audit(self,event_type:str,object_cid:Optional[str],detail:Mapping[str,Any]):
        previous=self._audit_root(); event_id=f"audit:{uuid.uuid4()}"; created=utc_now()
        body={"event_id":event_id,"previous_hash_sha256":previous,"event_type":event_type,
              "object_cid":object_cid,"detail":dict(detail),"created_at":created}
        event_hash=sha256_json(body)
        self.conn.execute("INSERT INTO local_audit(event_id,previous_hash_sha256,event_hash_sha256,event_type,object_cid,detail_json,created_at) VALUES(?,?,?,?,?,?,?)",
                          (event_id,previous,event_hash,event_type,object_cid,canonical_json(detail),created))
        return event_hash
    def store_local_object(self,envelope:Mapping[str,Any]):
        check=verify_encrypted_object(envelope,self.trusted_descriptors)
        if not check['valid']: raise ValueError(check)
        if envelope['origin_node_id'] != self.node_id: raise ValueError('local object origin mismatch')
        existing=self.conn.execute("SELECT 1 FROM objects WHERE cid=?",(envelope['cid'],)).fetchone()
        if existing: return {"status":"DUPLICATE","cid":envelope['cid']}
        self.conn.execute("INSERT INTO objects VALUES(?,?,?,?,?,?,?)",
                          (envelope['cid'],envelope['object_id'],envelope['origin_node_id'],envelope['classification'],
                           canonical_json(envelope),sha256_json(envelope),utc_now()))
        root=self._audit('object_stored',envelope['cid'],{"origin":"local","classification":envelope['classification']})
        self.conn.commit(); return {"status":"COMMITTED","cid":envelope['cid'],"audit_root_sha256":root}
    def decrypt(self,cid:str)->dict:
        if self.kms is None: raise RuntimeError('node has no KMS adapter')
        row=self.conn.execute("SELECT envelope_json FROM objects WHERE cid=?",(cid,)).fetchone()
        if not row: raise KeyError(cid)
        return decrypt_object(json.loads(row['envelope_json']),node_id=self.node_id,kms=self.kms,
                              trusted_descriptors=self.trusted_descriptors)
    def create_checkpoint(self,attestation:Mapping[str,Any])->dict:
        if self.identity_private_path is None: raise RuntimeError('signing key unavailable')
        attest_check=verify_attestation(attestation,self.descriptor)
        if not attest_check['valid']: raise ValueError(attest_check)
        prev=self.conn.execute("SELECT checkpoint_hash_sha256 FROM checkpoints ORDER BY checkpoint_sequence DESC LIMIT 1").fetchone()
        prev_hash=prev['checkpoint_hash_sha256'] if prev else '0'*64
        seq=(self.conn.execute("SELECT COALESCE(MAX(checkpoint_sequence),0)+1 AS n FROM checkpoints").fetchone()['n'])
        audit_seq=self.conn.execute("SELECT COALESCE(MAX(sequence),0) AS n FROM local_audit").fetchone()['n']
        core={"schema":"mmrf-vault-checkpoint-0.5","checkpoint_id":f"checkpoint:{self.node_id}:{seq}",
              "node_id":self.node_id,"checkpoint_sequence":seq,"previous_checkpoint_sha256":prev_hash,
              "audit_sequence":audit_seq,"audit_root_sha256":self._audit_root(),
              "attestation_sha256":sha256_json(attestation),"created_at":utc_now()}
        signature=load_ed25519_private(self.identity_private_path).sign(canonical_json(core).encode())
        checkpoint={**core,"signature_ed25519":b64(signature)}
        checkpoint_hash=sha256_json(checkpoint); checkpoint['checkpoint_hash_sha256']=checkpoint_hash
        self.conn.execute("INSERT INTO checkpoints VALUES(?,?,?,?,?,?,?,?,?)",
                          (seq,core['checkpoint_id'],prev_hash,audit_seq,core['audit_root_sha256'],core['attestation_sha256'],
                           checkpoint_hash,canonical_json(checkpoint),core['created_at']))
        self.conn.commit(); return checkpoint
    def _audit_segment(self,start_exclusive:int,end_inclusive:int)->list[dict]:
        rows=self.conn.execute("SELECT * FROM local_audit WHERE sequence>? AND sequence<=? ORDER BY sequence",
                               (start_exclusive,end_inclusive)).fetchall()
        return [{"sequence":r['sequence'],"event_id":r['event_id'],"previous_hash_sha256":r['previous_hash_sha256'],
                 "event_hash_sha256":r['event_hash_sha256'],"event_type":r['event_type'],"object_cid":r['object_cid'],
                 "detail":json.loads(r['detail_json']),"created_at":r['created_at']} for r in rows]
    def create_replication_bundle(self,*, peer_node_id:str,peer_audit_sequence:int,object_cids:Sequence[str],
                                  attestation:Mapping[str,Any],checkpoint:Mapping[str,Any])->dict:
        if self.identity_private_path is None: raise RuntimeError('signing key unavailable')
        objects=[]
        for cid in object_cids:
            row=self.conn.execute("SELECT envelope_json FROM objects WHERE cid=?",(cid,)).fetchone()
            if not row: raise KeyError(cid)
            env=json.loads(row['envelope_json'])
            if peer_node_id not in env['recipient_node_ids']:
                raise PermissionError(f'peer {peer_node_id} is not an object recipient')
            objects.append(env)
        core={"schema":"mmrf-replication-bundle-0.5","bundle_id":f"bundle:{uuid.uuid4()}",
              "origin_node_id":self.node_id,"recipient_node_id":peer_node_id,
              "origin_descriptor_sha256":self.descriptor['descriptor_sha256'],"attestation":attestation,
              "checkpoint":checkpoint,"audit_start_exclusive":peer_audit_sequence,
              "audit_events":self._audit_segment(peer_audit_sequence,checkpoint['audit_sequence']),
              "objects":objects,"created_at":utc_now()}
        signature=load_ed25519_private(self.identity_private_path).sign(canonical_json(core).encode())
        return {**core,"bundle_signature_ed25519":b64(signature),"bundle_sha256":sha256_json(core)}
    def receive_bundle(self,bundle:Mapping[str,Any])->dict:
        bundle_id=str(bundle.get('bundle_id','unknown'))
        def reject(reason,detail=None):
            self.conn.execute("INSERT OR REPLACE INTO replication_receipts VALUES(?,?,?,?,?)",
                              (bundle_id,str(bundle.get('origin_node_id','unknown')),'REJECTED',canonical_json({"reason":reason,**(detail or {})}),utc_now()))
            self.conn.commit(); return {"status":"REJECTED","reason":reason,**(detail or {})}
        if bundle.get('recipient_node_id') != self.node_id: return reject('wrong_recipient')
        if self.conn.execute("SELECT 1 FROM replication_receipts WHERE bundle_id=?",(bundle_id,)).fetchone():
            return {"status":"REJECTED","reason":"bundle_replay"}
        origin=bundle.get('origin_node_id')
        if origin not in self.trusted_descriptors: return reject('untrusted_origin')
        descriptor=self.trusted_descriptors[origin]
        core={k:v for k,v in bundle.items() if k not in {'bundle_signature_ed25519','bundle_sha256'}}
        try: load_ed25519_public(descriptor['identity_public_ed25519']).verify(unb64(bundle['bundle_signature_ed25519']),canonical_json(core).encode())
        except Exception as exc: return reject('bundle_signature_invalid',{"error":type(exc).__name__})
        if bundle.get('bundle_sha256') != sha256_json(core): return reject('bundle_hash_invalid')
        att=verify_attestation(bundle['attestation'],descriptor)
        if not att['valid']: return reject('attestation_invalid',{"attestation":att})
        checkpoint=bundle['checkpoint']; cp_core={k:v for k,v in checkpoint.items() if k not in {'signature_ed25519','checkpoint_hash_sha256'}}
        try: load_ed25519_public(descriptor['identity_public_ed25519']).verify(unb64(checkpoint['signature_ed25519']),canonical_json(cp_core).encode())
        except Exception as exc: return reject('checkpoint_signature_invalid',{"error":type(exc).__name__})
        cp_hash=sha256_json({k:v for k,v in checkpoint.items() if k!='checkpoint_hash_sha256'})
        if checkpoint.get('checkpoint_hash_sha256') != cp_hash: return reject('checkpoint_hash_invalid')
        if checkpoint.get('attestation_sha256') != sha256_json(bundle['attestation']): return reject('checkpoint_attestation_mismatch')
        peer=self.conn.execute("SELECT * FROM peer_state WHERE peer_node_id=?",(origin,)).fetchone()
        expected_cp_seq=(peer['checkpoint_sequence']+1) if peer else 1
        expected_prev_cp=peer['checkpoint_hash_sha256'] if peer else '0'*64
        expected_audit_seq=peer['audit_sequence'] if peer else 0
        expected_audit_root=peer['audit_root_sha256'] if peer else '0'*64
        if checkpoint['checkpoint_sequence'] != expected_cp_seq: return reject('checkpoint_sequence_not_monotonic',{"expected":expected_cp_seq})
        if checkpoint['previous_checkpoint_sha256'] != expected_prev_cp: return reject('checkpoint_chain_mismatch')
        if bundle['audit_start_exclusive'] != expected_audit_seq: return reject('audit_start_mismatch')
        current=expected_audit_root; seq=expected_audit_seq
        for event in bundle['audit_events']:
            seq += 1
            if event['sequence'] != seq or event['previous_hash_sha256'] != current: return reject('audit_segment_discontinuity',{"sequence":seq})
            body={"event_id":event['event_id'],"previous_hash_sha256":current,"event_type":event['event_type'],
                  "object_cid":event['object_cid'],"detail":event['detail'],"created_at":event['created_at']}
            computed=sha256_json(body)
            if event['event_hash_sha256'] != computed: return reject('audit_event_hash_invalid',{"sequence":seq})
            current=computed
        if seq != checkpoint['audit_sequence'] or current != checkpoint['audit_root_sha256']:
            return reject('checkpoint_audit_root_mismatch')
        for env in bundle['objects']:
            check=verify_encrypted_object(env,self.trusted_descriptors)
            if not check['valid']: return reject('encrypted_object_invalid',{"object":env.get('cid'),"check":check})
            if self.node_id not in env['recipient_node_ids']: return reject('node_not_authorized_for_object',{"object":env['cid']})
        stored=0
        self.conn.execute('BEGIN IMMEDIATE')
        try:
            for env in bundle['objects']:
                if not self.conn.execute("SELECT 1 FROM objects WHERE cid=?",(env['cid'],)).fetchone():
                    self.conn.execute("INSERT INTO objects VALUES(?,?,?,?,?,?,?)",
                                      (env['cid'],env['object_id'],env['origin_node_id'],env['classification'],canonical_json(env),sha256_json(env),utc_now()))
                    stored += 1
            self.conn.execute("INSERT OR REPLACE INTO peer_state VALUES(?,?,?,?,?,?)",
                              (origin,checkpoint['checkpoint_sequence'],checkpoint['checkpoint_hash_sha256'],checkpoint['audit_sequence'],checkpoint['audit_root_sha256'],utc_now()))
            self.conn.execute("INSERT INTO replication_receipts VALUES(?,?,?,?,?)",
                              (bundle_id,origin,'ACCEPTED',canonical_json({"stored_objects":stored,"checkpoint":checkpoint['checkpoint_sequence']}),utc_now()))
            self._audit('replication_received',None,{"origin_node_id":origin,"bundle_id":bundle_id,"stored_objects":stored})
            self.conn.commit()
        except Exception:
            self.conn.rollback(); raise
        return {"status":"ACCEPTED","bundle_id":bundle_id,"stored_objects":stored,
                "origin_checkpoint_sequence":checkpoint['checkpoint_sequence'],"origin_audit_sequence":checkpoint['audit_sequence']}
    def verify_local_audit(self)->dict:
        current='0'*64; count=0
        for r in self.conn.execute("SELECT * FROM local_audit ORDER BY sequence"):
            body={"event_id":r['event_id'],"previous_hash_sha256":current,"event_type":r['event_type'],
                  "object_cid":r['object_cid'],"detail":json.loads(r['detail_json']),"created_at":r['created_at']}
            computed=sha256_json(body)
            if r['previous_hash_sha256']!=current or r['event_hash_sha256']!=computed:
                return {"valid":False,"count":count,"failed_sequence":r['sequence']}
            current=computed; count+=1
        return {"valid":True,"count":count,"audit_root_sha256":current}
    def stats(self)->dict:
        def count(t): return self.conn.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()['n']
        return {"node_id":self.node_id,"objects":count('objects'),"local_audit_events":count('local_audit'),
                "checkpoints":count('checkpoints'),"peer_states":count('peer_state'),
                "replication_receipts":count('replication_receipts'),"local_audit":self.verify_local_audit()}
