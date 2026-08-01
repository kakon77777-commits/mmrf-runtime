from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mmrf_data_lake import (
    DataLake,
    EmptyShardSelection,
    ScientificQueryGuard,
)


ROOT = Path(__file__).resolve().parents[1]


def lake(args) -> DataLake:
    return DataLake(
        root_dir=Path(args.lake_root),
        index_db=Path(args.index_database),
        shard_size=args.shard_size,
    )


def cmd_append(args) -> None:
    instance = lake(args)
    result = instance.append_generation(
        limit_exclusive=args.limit,
        generation=args.generation,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    instance.close()


def cmd_query(args) -> None:
    instance = lake(args)
    manifest = instance.current_manifest()
    guard = ScientificQueryGuard(
        shard_count=manifest["shard_count"],
        default_budget=args.budget,
    )
    request = (
        json.loads(Path(args.request).read_text(encoding="utf-8"))
        if args.request
        else json.load(sys.stdin)
    )
    try:
        result = instance.execute_query(
            request,
            session_id=args.session,
            guard=guard,
            workflow_dir=Path(args.workflow_dir),
        )
    except EmptyShardSelection as exc:
        # Report it as a query outcome rather than a traceback, so a replay
        # script sees a structured refusal and a non-zero exit instead of an
        # unhandled exception.
        result = {
            "schema": "mmrf-scientific-query-response-0.8",
            "status": "NO_DATA",
            "query": request,
            "reason": str(exc),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        instance.close()
        raise SystemExit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    instance.close()
    raise SystemExit(0 if result["status"] == "OK" else 2)


def cmd_verify(args) -> None:
    instance = lake(args)
    result = {
        "manifest_chain": instance.verify_manifest_chain(),
        "query_audit": instance.verify_query_audit(),
        "sample": instance.integrity_sample(
            sample_count=args.sample_count,
            seed=args.seed,
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    instance.close()
    raise SystemExit(
        0 if all(
            item["valid"] for item in result.values()
        ) else 1
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="mmrf-lake")
    parser.add_argument(
        "--lake-root",
        default=str(ROOT / "lake_data" / "primary"),
    )
    parser.add_argument(
        "--index-database",
        default=str(ROOT / "lake_state" / "lake_index.sqlite"),
    )
    parser.add_argument("--shard-size", type=int, default=100_000)
    parser.add_argument(
        "--workflow-dir",
        default=str(ROOT / "workflows"),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    append = sub.add_parser("append")
    append.add_argument("--limit", type=int, required=True)
    append.add_argument("--generation", type=int, required=True)
    append.set_defaults(func=cmd_append)

    query = sub.add_parser("query")
    query.add_argument("--request")
    query.add_argument("--session", default="scientific-cli")
    query.add_argument("--budget", type=int, default=120)
    query.set_defaults(func=cmd_query)

    verify = sub.add_parser("verify")
    verify.add_argument("--sample-count", type=int, default=8)
    verify.add_argument("--seed", type=int, default=20260729)
    verify.set_defaults(func=cmd_verify)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
