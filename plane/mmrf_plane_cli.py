from __future__ import annotations

import argparse
import json
from pathlib import Path

from mmrf_transparency_recovery import (
    TransparencyLog,
    generate_epoch_node_material,
    generate_witness_material,
    create_recovery_escrow,
)


def main() -> None:
    parser = argparse.ArgumentParser(prog="mmrf-plane")
    sub = parser.add_subparsers(dest="command", required=True)

    node = sub.add_parser("generate-node")
    node.add_argument("--node-id", required=True)
    node.add_argument("--epoch", type=int, required=True)
    node.add_argument("--private-dir", required=True)
    node.add_argument("--public-dir", required=True)
    node.add_argument("--measurement", action="append", required=True)

    witness = sub.add_parser("generate-witness")
    witness.add_argument("--witness-id", required=True)
    witness.add_argument("--private-dir", required=True)
    witness.add_argument("--public-dir", required=True)

    log = sub.add_parser("init-log")
    log.add_argument("--database", required=True)
    log.add_argument("--log-id", required=True)
    log.add_argument("--private-key", required=True)
    log.add_argument("--public-key", required=True)

    args = parser.parse_args()

    if args.command == "generate-node":
        result = generate_epoch_node_material(
            node_id=args.node_id,
            key_epoch=args.epoch,
            private_dir=Path(args.private_dir),
            public_dir=Path(args.public_dir),
            roles=["vault"],
            accepted_measurements=args.measurement,
        )
    elif args.command == "generate-witness":
        result = generate_witness_material(
            witness_id=args.witness_id,
            private_dir=Path(args.private_dir),
            public_dir=Path(args.public_dir),
        )
    else:
        result = TransparencyLog.generate_keypair(
            Path(args.private_key),
            Path(args.public_key),
        )
        log_instance = TransparencyLog(
            Path(args.database),
            args.log_id,
            Path(args.private_key),
            Path(args.public_key),
        )
        log_instance.init_schema()
        log_instance.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
