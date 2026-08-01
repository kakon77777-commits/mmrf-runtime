from __future__ import annotations

import argparse
import json
import os
import signal
import ssl
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping

from mmrf_policy_network import (
    canonical_json,
    create_client_ssl_context,
    create_policy_snapshot,
    create_server_ssl_context,
    load_ed25519_private,
    node_state_from_policy,
    sha256_json,
    validate_replication_message,
    verify_policy_snapshot,
)
from mmrf_transparency_recovery import (
    merkle_root,
    verify_sth_signature,
)


def atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def peer_common_name(handler: BaseHTTPRequestHandler) -> str:
    certificate = handler.connection.getpeercert()
    for rdn in certificate.get("subject", []):
        for key, value in rdn:
            if key == "commonName":
                return value
    return ""


def read_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    body = handler.rfile.read(length) if length else b"{}"
    return json.loads(body)


def respond(handler: BaseHTTPRequestHandler, status: int, value: Mapping[str, Any]) -> None:
    payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


class QuietHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return


def run_authority(args: argparse.Namespace) -> None:
    policy_path = Path(args.policy_file)
    lock = threading.Lock()

    class Handler(QuietHandler):
        def do_GET(self) -> None:
            if self.path == "/health":
                respond(self, 200, {"status": "ok", "service": "authority"})
                return
            if self.path != "/policy":
                respond(self, 404, {"error": "not_found"})
                return
            policy = read_json(policy_path)
            if policy is None:
                respond(self, 503, {"error": "policy_not_published"})
            else:
                respond(self, 200, policy)

        def do_POST(self) -> None:
            if self.path != "/admin/publish":
                respond(self, 404, {"error": "not_found"})
                return
            if peer_common_name(self) != "policy-admin":
                respond(self, 403, {"error": "admin_certificate_required"})
                return
            request = read_body(self)
            with lock:
                current = read_json(policy_path)
                version = 1 if current is None else int(current["policy_version"]) + 1
                previous = "0" * 64 if current is None else current["snapshot_sha256"]
                snapshot = create_policy_snapshot(
                    private_key_path=Path(args.policy_private_key),
                    version=version,
                    active_nodes=request["active_nodes"],
                    revoked_nodes=request.get("revoked_nodes", []),
                    allowed_measurements=request["allowed_measurements"],
                    witness_threshold=int(request.get("witness_threshold", 2)),
                    previous_snapshot_sha256=previous,
                    ttl_seconds=int(request.get("ttl_seconds", 300)),
                )
                atomic_write_json(policy_path, snapshot)
            respond(self, 200, snapshot)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.socket = create_server_ssl_context(
        ca_certificate_path=Path(args.ca_cert),
        certificate_path=Path(args.cert),
        private_key_path=Path(args.key),
    ).wrap_socket(server.socket, server_side=True)
    server.serve_forever()


def run_node(args: argparse.Namespace) -> None:
    state_path = Path(args.state_file)
    objects_path = Path(args.objects_file)
    current_policy_path = Path(args.local_policy_file)
    lock = threading.Lock()
    stop = threading.Event()

    initial_state = {
        "node_id": args.node_id,
        "status": "WAITING_FOR_POLICY",
        "policy_version": 0,
        "updated_at": None,
    }
    atomic_write_json(state_path, initial_state)

    client_context = create_client_ssl_context(
        ca_certificate_path=Path(args.ca_cert),
        certificate_path=Path(args.cert),
        private_key_path=Path(args.key),
    )

    def poll() -> None:
        import urllib.request
        while not stop.is_set():
            try:
                request = urllib.request.Request(
                    args.authority_url + "/policy",
                    headers={"Accept": "application/json"},
                )
                with urllib.request.urlopen(
                    request,
                    context=client_context,
                    timeout=2,
                ) as response:
                    snapshot = json.loads(response.read())
                with lock:
                    current = read_json(current_policy_path)
                    if current is None:
                        verification = verify_policy_snapshot(
                            snapshot,
                            public_key_path=Path(args.policy_public_key),
                            current_snapshot=None,
                        )
                    elif int(snapshot["policy_version"]) > int(current["policy_version"]):
                        verification = verify_policy_snapshot(
                            snapshot,
                            public_key_path=Path(args.policy_public_key),
                            current_snapshot=current,
                        )
                    elif snapshot["snapshot_sha256"] == current["snapshot_sha256"]:
                        verification = {"valid": True}
                    else:
                        verification = {
                            "valid": False,
                            "reason": "policy_rollback_or_equivocation",
                        }
                    if verification["valid"]:
                        atomic_write_json(current_policy_path, snapshot)
                        state = node_state_from_policy(
                            node_id=args.node_id,
                            measurement_sha256=args.measurement,
                            policy=snapshot,
                        )
                        atomic_write_json(state_path, state)
            except Exception:
                pass
            stop.wait(args.poll_interval)

    polling_thread = threading.Thread(target=poll, daemon=True)
    polling_thread.start()

    class Handler(QuietHandler):
        def do_GET(self) -> None:
            if self.path == "/health":
                respond(self, 200, {"status": "ok", "service": "node", "node_id": args.node_id})
            elif self.path == "/status":
                respond(self, 200, read_json(state_path, initial_state))
            else:
                respond(self, 404, {"error": "not_found"})

        def do_POST(self) -> None:
            if self.path != "/replicate":
                respond(self, 404, {"error": "not_found"})
                return
            message = read_body(self)
            policy = read_json(current_policy_path)
            state = read_json(state_path, initial_state)
            if policy is None:
                respond(self, 503, {"error": "no_policy"})
                return
            if state.get("status") != "ACTIVE":
                respond(self, 403, {
                    "error": "recipient_not_active",
                    "node_status": state.get("status"),
                })
                return
            validation = validate_replication_message(
                message,
                peer_common_name=peer_common_name(self),
                recipient_node_id=args.node_id,
                policy=policy,
            )
            if not validation["valid"]:
                respond(self, 403, validation)
                return
            objects_path.parent.mkdir(parents=True, exist_ok=True)
            with objects_path.open("a", encoding="utf-8") as handle:
                handle.write(canonical_json({
                    "received_at": time.time(),
                    "peer_common_name": peer_common_name(self),
                    "message": message,
                    "message_sha256": sha256_json(message),
                }) + "\n")
            respond(self, 202, {
                "status": "ACCEPTED",
                "node_id": args.node_id,
                "message_sha256": sha256_json(message),
            })

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.socket = create_server_ssl_context(
        ca_certificate_path=Path(args.ca_cert),
        certificate_path=Path(args.cert),
        private_key_path=Path(args.key),
    ).wrap_socket(server.socket, server_side=True)
    try:
        server.serve_forever()
    finally:
        stop.set()


def run_witness(args: argparse.Namespace) -> None:
    state_path = Path(args.state_file)
    lock = threading.Lock()
    atomic_write_json(state_path, {
        "witness_id": args.witness_id,
        "tree_size": 0,
        "root_hash_sha256": None,
        "sth_sha256": None,
    })

    class Handler(QuietHandler):
        def do_GET(self) -> None:
            if self.path == "/health":
                respond(self, 200, {"status": "ok", "service": "witness"})
            elif self.path == "/head":
                respond(self, 200, read_json(state_path))
            else:
                respond(self, 404, {"error": "not_found"})

        def do_POST(self) -> None:
            if self.path != "/gossip":
                respond(self, 404, {"error": "not_found"})
                return
            request = read_body(self)
            sth = request["sth"]
            entries = request["entries"]
            if not verify_sth_signature(sth, Path(args.log_public_key)):
                respond(self, 403, {"accepted": False, "reason": "log_signature_invalid"})
                return
            if int(sth["tree_size"]) != len(entries):
                respond(self, 403, {"accepted": False, "reason": "tree_size_mismatch"})
                return
            if merkle_root(entries) != sth["root_hash_sha256"]:
                respond(self, 403, {"accepted": False, "reason": "root_mismatch"})
                return
            with lock:
                prior = read_json(state_path)
                if int(sth["tree_size"]) < int(prior["tree_size"]):
                    result = {"accepted": False, "reason": "tree_size_rollback"}
                elif int(sth["tree_size"]) == int(prior["tree_size"]):
                    if sth["root_hash_sha256"] != prior["root_hash_sha256"]:
                        result = {"accepted": False, "reason": "equivocation_detected"}
                    else:
                        result = {"accepted": True, "reason": "already_observed"}
                elif int(prior["tree_size"]) > 0 and (
                    sth["previous_sth_sha256"] != prior["sth_sha256"]
                ):
                    result = {"accepted": False, "reason": "sth_chain_mismatch"}
                else:
                    atomic_write_json(state_path, {
                        "witness_id": args.witness_id,
                        "tree_size": sth["tree_size"],
                        "root_hash_sha256": sth["root_hash_sha256"],
                        "sth_sha256": sth["sth_sha256"],
                        "received_from": peer_common_name(self),
                        "updated_at": time.time(),
                    })
                    result = {"accepted": True, "reason": None}
            respond(self, 200 if result["accepted"] else 409, result)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.socket = create_server_ssl_context(
        ca_certificate_path=Path(args.ca_cert),
        certificate_path=Path(args.cert),
        private_key_path=Path(args.key),
    ).wrap_socket(server.socket, server_side=True)
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(prog="mmrf-network-service")
    sub = parser.add_subparsers(dest="mode", required=True)

    authority = sub.add_parser("authority")
    authority.add_argument("--port", type=int, required=True)
    authority.add_argument("--ca-cert", required=True)
    authority.add_argument("--cert", required=True)
    authority.add_argument("--key", required=True)
    authority.add_argument("--policy-private-key", required=True)
    authority.add_argument("--policy-file", required=True)

    node = sub.add_parser("node")
    node.add_argument("--node-id", required=True)
    node.add_argument("--port", type=int, required=True)
    node.add_argument("--ca-cert", required=True)
    node.add_argument("--cert", required=True)
    node.add_argument("--key", required=True)
    node.add_argument("--authority-url", required=True)
    node.add_argument("--policy-public-key", required=True)
    node.add_argument("--measurement", required=True)
    node.add_argument("--state-file", required=True)
    node.add_argument("--objects-file", required=True)
    node.add_argument("--local-policy-file", required=True)
    node.add_argument("--poll-interval", type=float, default=0.05)

    witness = sub.add_parser("witness")
    witness.add_argument("--witness-id", required=True)
    witness.add_argument("--port", type=int, required=True)
    witness.add_argument("--ca-cert", required=True)
    witness.add_argument("--cert", required=True)
    witness.add_argument("--key", required=True)
    witness.add_argument("--log-public-key", required=True)
    witness.add_argument("--state-file", required=True)

    args = parser.parse_args()
    if args.mode == "authority":
        run_authority(args)
    elif args.mode == "node":
        run_node(args)
    else:
        run_witness(args)


if __name__ == "__main__":
    main()
