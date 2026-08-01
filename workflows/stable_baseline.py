#!/usr/bin/env python3
"""Aggregate baseline study computed directly from the stable dataset.

Why this exists
---------------
`workflows/prime-distribution-baseline.workflow.json` describes the same four
aggregate operations, but it runs through the data-lake query layer, and the
lake index (`lake_state/lake_index.sqlite`) and the generation-1 lake shards
(`lake_data/primary/shards/`) are not part of the v1.0 stable or public-profile
packages. Only the promoted generation-2 dataset under `stable_data/shards/`
ships. So the published workflow cannot be replayed from the published package.

This script closes that gap without changing the frozen dataset or inventing a
new lake generation: it reads the stable shards directly and computes the same
four aggregates.

It stays inside the public safety boundary. Every output is an aggregate over
the whole registered range. There is no target integer input, no factor
candidate, no range narrowing, and no source-to-factor relation.

Usage
-----
    python workflows/stable_baseline.py --project-root . \
        --output results_v10/stable_baseline_output.json

The output is canonicalised (sorted keys, no insignificant whitespace) and its
SHA-256 is recorded inside the result under `output_sha256`, computed over the
result body with that field excluded — the same self-referential exclusion the
stable manifest uses.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np

WORKFLOW_ID = "stable-baseline"
WORKFLOW_VERSION = "1.0.0"

# Imported rather than restated, so this study and the lake query surface can
# never disagree about what a family name means.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lake"))
from mmrf_data_lake import FAMILY_BITS  # noqa: E402


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def load_stable(project_root: Path):
    manifest_path = project_root / "stable_data" / "stable_manifest_v1.0.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    core = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    if manifest.get("manifest_sha256") != sha256_json(core):
        raise SystemExit("stable manifest failed its own hash check; refusing to run")

    shard_dir = project_root / "stable_data" / "shards"
    shards = sorted(shard_dir.glob("*.npz"))
    if len(shards) != manifest["shard_count"]:
        raise SystemExit(
            f"manifest declares {manifest['shard_count']} shards, "
            f"found {len(shards)} on disk; refusing to run"
        )
    return manifest, shards


def main() -> int:
    parser = argparse.ArgumentParser(prog="stable_baseline")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    manifest, shard_paths = load_stable(root)

    columns = (
        "prime",
        "previous_gap",
        "residue_6",
        "residue_30",
        "residue_210",
        "decimal_digits",
        "family_flags",
        "wheel30_class",
    )
    parts = {c: [] for c in columns}
    for path in shard_paths:
        with np.load(path) as handle:
            for c in columns:
                parts[c].append(handle[c])
    data = {c: np.concatenate(v) for c, v in parts.items()}

    prime_count = int(len(data["prime"]))
    if prime_count != manifest["prime_count"]:
        raise SystemExit(
            f"manifest declares {manifest['prime_count']} primes, "
            f"shards hold {prime_count}; refusing to run"
        )

    limit = int(manifest["limit_exclusive"])
    gaps = data["previous_gap"]
    gaps = gaps[gaps > 0]

    def tally(array):
        return {
            str(int(v)): int(c) for v, c in zip(*np.unique(array, return_counts=True))
        }

    residue_counts = {
        "6": tally(data["residue_6"]),
        "30": tally(data["residue_30"]),
        "210": tally(data["residue_210"]),
    }
    gap_histogram = tally(gaps)

    # Order-of-magnitude comparison. `decimal_digits` is a stored column, so the
    # band boundaries are the dataset's own, not re-derived here.
    magnitude_bands = []
    for digits, count in sorted(
        tally(data["decimal_digits"]).items(), key=lambda kv: int(kv[0])
    ):
        d = int(digits)
        low, high = 10 ** (d - 1), min(10**d, limit)
        if d == 1:
            low = 0
        magnitude_bands.append(
            {
                "decimal_digits": d,
                "range_start": low,
                "range_end_exclusive": high,
                "prime_count": count,
                "density": count / (high - low),
            }
        )

    wheel_counts = {}
    for value, count in zip(*np.unique(data["wheel30_class"], return_counts=True)):
        wheel_counts[str(int(value))] = int(count)

    flags = data["family_flags"].astype(np.int64)
    families = {
        name: int(np.count_nonzero(flags & mask))
        for name, mask in FAMILY_BITS.items()
    }

    # Every bit the column actually carries must map to a named family. If a
    # future generation sets a bit this build of FAMILY_BITS does not know, the
    # study would silently under-report rather than say so.
    known = 0
    for mask in FAMILY_BITS.values():
        known |= mask
    unknown = int(np.bitwise_or.reduce(flags)) & ~known
    if unknown:
        raise SystemExit(
            f"family_flags carries unnamed bits (mask {unknown:#b}); "
            f"this dataset generation encodes families this build cannot name"
        )

    body = {
        "schema": "mmrf-stable-baseline-1.0",
        "workflow_id": WORKFLOW_ID,
        "workflow_version": WORKFLOW_VERSION,
        "dataset_id": manifest["dataset_id"],
        "generation": manifest["generation"],
        "stable_manifest_sha256": manifest["manifest_sha256"],
        "range": {"start": 0, "end_exclusive": limit},
        "shard_count": int(manifest["shard_count"]),
        "interval_density": {
            "prime_count": prime_count,
            "width": limit,
            "density": prime_count / limit,
        },
        "gap_quantiles": {
            "sample_size": int(len(gaps)),
            "max_gap": int(gaps.max()),
            "mean_gap": float(gaps.mean()),
            "quantiles": {
                str(q): float(np.quantile(gaps, q)) for q in (0.5, 0.9, 0.99)
            },
        },
        "gap_histogram": gap_histogram,
        "residue_distribution": residue_counts,
        "wheel30_class_distribution": wheel_counts,
        "magnitude_bands": magnitude_bands,
        "family_counts": families,
        "family_counting_note": (
            "Each pair family is counted at its larger observed member, which "
            "keeps prior shards immutable during append."
        ),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.system(),
        },
        "safety": {
            "aggregate_only": True,
            "target_conditioned_queries": False,
            "factor_candidates_emitted": False,
            "range_narrowing_emitted": False,
        },
    }

    result = {**body, "output_sha256": sha256_json(body)}
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"wrote {out}  output_sha256={result['output_sha256']}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
