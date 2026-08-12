"""Audit cumulative ordinal continuity across the complete MMRF candidate chain."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_manifest_entries() -> list[tuple[int, Path, dict]]:
    entries = []
    for path in (ROOT / "research_candidates").glob("*/candidate_manifest.json"):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        entries.append((int(manifest["candidate_generation"]), path.parent, manifest))
    return entries


def select_manifest_chain(
    entries: list[tuple[int, Path, dict]], tip_candidate_dir: Path | None
) -> list[tuple[int, Path, dict]]:
    if tip_candidate_dir is None:
        return sorted(entries, key=lambda item: item[0])

    tip_directory = tip_candidate_dir
    if not tip_directory.is_absolute():
        tip_directory = ROOT / tip_directory
    tip_directory = tip_directory.resolve()
    tip_directory.relative_to(ROOT)
    tip_manifest_path = tip_directory / "candidate_manifest.json"
    if not tip_manifest_path.is_file():
        raise SystemExit(f"tip_candidate_manifest_missing:{tip_manifest_path}")

    by_sha = {entry[2]["manifest_sha256"]: entry for entry in entries}
    tip_manifest = json.loads(tip_manifest_path.read_text(encoding="utf-8"))
    current_sha = tip_manifest["manifest_sha256"]
    selected = []
    seen = set()
    while current_sha:
        if current_sha in seen:
            raise SystemExit(f"candidate_chain_cycle:{current_sha}")
        seen.add(current_sha)
        entry = by_sha.get(current_sha)
        if entry is None:
            raise SystemExit(f"candidate_chain_manifest_missing:{current_sha}")
        selected.append(entry)
        current_sha = entry[2].get("prior_candidate_manifest_sha256")
    selected.reverse()
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--tip-candidate-dir",
        type=Path,
        help="Follow prior manifest hashes from this candidate and audit that exact chain.",
    )
    args = parser.parse_args()

    base = json.loads(
        (ROOT / "stable_data" / "stable_manifest_v1.0.json").read_text(encoding="utf-8")
    )
    manifests = select_manifest_chain(load_manifest_entries(), args.tip_candidate_dir)

    expected_ordinal = int(base["prime_count"]) + 1
    expected_generation = int(base["generation"]) + 1
    expected_start = int(base["limit_exclusive"])
    expected_shard = int(base["shard_count"])
    previous_sha = None
    entries = []
    for generation, directory, manifest in manifests:
        record = manifest["shards"][0]
        with np.load(ROOT / record["file_path"], allow_pickle=False) as archive:
            ordinals = np.asarray(archive["ordinal"], dtype=np.int64)
            prime_count = len(archive["prime"])
        actual_first = int(ordinals[0])
        actual_last = int(ordinals[-1])
        expected_last = expected_ordinal + prime_count - 1
        manifest_core = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
        checks = {
            "manifest_hash_ok": sha256_json(manifest_core) == manifest["manifest_sha256"],
            "base_manifest_binding": manifest["base_manifest_sha256"] == base["manifest_sha256"],
            "generation_continuity": generation == expected_generation,
            "range_continuity": int(manifest["range_start"]) == expected_start,
            "shard_index_continuity": int(record["shard_index"]) == expected_shard,
            "prior_manifest_binding": (
                previous_sha is None
                and "prior_candidate_manifest_sha256" not in manifest
            ) or manifest.get("prior_candidate_manifest_sha256") == previous_sha,
            "full_chain_ordinal_continuity": actual_first == expected_ordinal
            and actual_last == expected_last
            and bool(np.all(np.diff(ordinals) == 1)),
        }
        entries.append({
            "candidate_generation": generation,
            "candidate_directory": str(directory.relative_to(ROOT)).replace("\\", "/"),
            "candidate_manifest_sha256": manifest["manifest_sha256"],
            "range": [int(manifest["range_start"]), int(manifest["range_end_exclusive"])],
            "prime_count": prime_count,
            "expected_ordinal": [expected_ordinal, expected_last],
            "actual_ordinal": [actual_first, actual_last],
            "ordinal_offset": actual_first - expected_ordinal,
            "checks": checks,
            "valid": all(checks.values()),
        })
        expected_ordinal = expected_last + 1
        expected_generation += 1
        expected_start = int(manifest["range_end_exclusive"])
        expected_shard += 1
        previous_sha = manifest["manifest_sha256"]

    core = {
        "schema": "mmrf-prime-expansion-chain-audit-1.0",
        "as_of": args.as_of,
        "base_manifest_sha256": base["manifest_sha256"],
        "selected_chain_tip": manifests[-1][2]["manifest_sha256"] if manifests else None,
        "entries": entries,
        "valid": all(entry["valid"] for entry in entries),
        "first_invalid_generation": next(
            (entry["candidate_generation"] for entry in entries if not entry["valid"]),
            None,
        ),
    }
    audit = {**core, "audit_sha256": sha256_json(core)}
    output = args.output.resolve()
    output.relative_to(ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0 if audit["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
