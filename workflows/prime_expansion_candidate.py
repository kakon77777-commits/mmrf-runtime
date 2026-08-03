"""Generate and independently verify one append-only MMRF prime shard.

This workflow creates a research candidate only. It never edits the frozen
v1.0 manifest or promotes a new public generation. The candidate uses the
v0.9 logical column schema already bound by the v1.0 release, and it leaves a
machine-readable verification record plus a human-readable handoff for the
next relay agent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mmrf_stable.runtime import validate_stable_dataset_manifest  # noqa: E402


V09_COLUMNS = (
    "prime",
    "ordinal",
    "bit_length",
    "decimal_digits",
    "previous_gap",
    "residue_6",
    "residue_30",
    "residue_210",
    "family_flags",
    "wheel30_class",
)

FAMILY_BITS = {
    "twin_prime": 1,
    "cousin_prime": 2,
    "sexy_prime": 4,
    "safe_prime": 8,
}

WHEEL30_CLASSES = {
    1: 0,
    7: 1,
    11: 2,
    13: 3,
    17: 4,
    19: 5,
    23: 6,
    29: 7,
}


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(value) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def numpy_sieve(limit_exclusive: int) -> np.ndarray:
    flags = np.ones(limit_exclusive, dtype=np.bool_)
    flags[:2] = False
    for value in range(2, math.isqrt(limit_exclusive - 1) + 1):
        if flags[value]:
            flags[value * value:limit_exclusive:value] = False
    return np.flatnonzero(flags).astype(np.int64)


def python_base_primes(limit: int) -> list[int]:
    flags = bytearray(b"\x01") * (limit + 1)
    if limit >= 0:
        flags[0] = 0
    if limit >= 1:
        flags[1] = 0
    for value in range(2, math.isqrt(limit) + 1):
        if flags[value]:
            flags[value * value:limit + 1:value] = b"\x00" * (
                ((limit - value * value) // value) + 1
            )
    return [value for value, flag in enumerate(flags) if flag]


def segmented_primes(start: int, end: int) -> list[int]:
    flags = bytearray(b"\x01") * (end - start)
    for prime in python_base_primes(math.isqrt(end - 1)):
        first = max(prime * prime, ((start + prime - 1) // prime) * prime)
        for composite in range(first, end, prime):
            flags[composite - start] = 0
    return [
        start + offset
        for offset, flag in enumerate(flags)
        if flag and start + offset >= 2
    ]


def canonical_array_content_sha256(arrays: dict[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    digest.update(b"MMRF-NPZ-COLUMNAR-0.9\0")
    for name in V09_COLUMNS:
        array = np.ascontiguousarray(arrays[name])
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(str(array.dtype).encode("ascii") + b"\0")
        digest.update(canonical_json(list(array.shape)).encode("ascii"))
        digest.update(b"\0")
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def load_stable_primes(manifest: dict) -> np.ndarray:
    primes = []
    for shard in manifest["shards"]:
        path = ROOT / shard["file_path"]
        with np.load(path, allow_pickle=False) as archive:
            primes.append(np.asarray(archive["prime"], dtype=np.int64))
    result = np.concatenate(primes)
    if len(result) != int(manifest["prime_count"]):
        raise SystemExit("stable_prime_count_mismatch")
    return result


def load_prior_candidate(candidate_dir: Path, stable_manifest: dict) -> tuple[dict, np.ndarray]:
    candidate_dir = candidate_dir.resolve()
    try:
        candidate_dir.relative_to(ROOT)
    except ValueError as exc:
        raise SystemExit("prior_candidate_must_be_inside_project_root") from exc
    manifest_path = candidate_dir / "candidate_manifest.json"
    review_path = candidate_dir / "independent_review.json"
    if not manifest_path.exists() or not review_path.exists():
        raise SystemExit("prior_candidate_requires_manifest_and_independent_review")
    candidate = json.loads(manifest_path.read_text(encoding="utf-8"))
    review = json.loads(review_path.read_text(encoding="utf-8"))
    candidate_core = {key: value for key, value in candidate.items() if key != "manifest_sha256"}
    if candidate.get("manifest_sha256") != sha256_json(candidate_core):
        raise SystemExit("prior_candidate_manifest_hash_mismatch")
    if candidate.get("base_manifest_sha256") != stable_manifest.get("manifest_sha256"):
        raise SystemExit("prior_candidate_stable_base_binding_mismatch")
    if candidate.get("status") != "CANDIDATE_UNPROMOTED" or review.get("valid") is not True:
        raise SystemExit("prior_candidate_independent_review_required")
    if review.get("candidate_manifest_sha256") != candidate["manifest_sha256"]:
        raise SystemExit("prior_candidate_review_binding_mismatch")
    if len(candidate.get("shards", [])) != 1:
        raise SystemExit("prior_candidate_must_contain_one_shard")
    record = candidate["shards"][0]
    shard_path = ROOT / record["file_path"]
    with np.load(shard_path, allow_pickle=False) as archive:
        primes = np.asarray(archive["prime"], dtype=np.int64)
    if len(primes) != int(record["row_count"]):
        raise SystemExit("prior_candidate_row_count_mismatch")
    return candidate, primes


def build_candidate_arrays(
    all_primes: np.ndarray,
    base_count: int,
    start: int,
    end: int,
) -> dict[str, np.ndarray]:
    left = int(np.searchsorted(all_primes, start, side="left"))
    right = int(np.searchsorted(all_primes, end, side="left"))
    primes = all_primes[left:right]
    prime_set = set(int(value) for value in all_primes)

    previous_gap = np.zeros(len(primes), dtype=np.uint32)
    previous_gap[0] = int(primes[0] - all_primes[left - 1])
    if len(primes) > 1:
        previous_gap[1:] = np.diff(primes).astype(np.uint32)

    family_flags = np.zeros(len(primes), dtype=np.uint8)
    for index, value in enumerate(primes):
        prime = int(value)
        mask = 0
        if prime - 2 in prime_set:
            mask |= FAMILY_BITS["twin_prime"]
        if prime - 4 in prime_set:
            mask |= FAMILY_BITS["cousin_prime"]
        if prime - 6 in prime_set:
            mask |= FAMILY_BITS["sexy_prime"]
        if prime > 2 and (prime - 1) // 2 in prime_set:
            mask |= FAMILY_BITS["safe_prime"]
        family_flags[index] = mask

    wheel30_class = np.array(
        [WHEEL30_CLASSES.get(int(value % 30), 255) for value in primes],
        dtype=np.uint8,
    )
    return {
        "prime": primes.astype(np.int64),
        "ordinal": np.arange(base_count + 1, base_count + 1 + len(primes), dtype=np.int64),
        "bit_length": np.array([int(value).bit_length() for value in primes], dtype=np.uint8),
        "decimal_digits": np.array([len(str(int(value))) for value in primes], dtype=np.uint8),
        "previous_gap": previous_gap,
        "residue_6": (primes % 6).astype(np.uint8),
        "residue_30": (primes % 30).astype(np.uint8),
        "residue_210": (primes % 210).astype(np.uint16),
        "family_flags": family_flags,
        "wheel30_class": wheel30_class,
    }


def verify_arrays(
    arrays: dict[str, np.ndarray],
    all_primes: np.ndarray,
    base_count: int,
    start: int,
    end: int,
) -> dict:
    primes = arrays["prime"]
    expected = all_primes[
        np.searchsorted(all_primes, start, side="left"):
        np.searchsorted(all_primes, end, side="left")
    ]
    segmented = np.asarray(segmented_primes(start, end), dtype=np.int64)
    checks = {
        "range_ok": bool(len(primes) and primes[0] >= start and primes[-1] < end),
        "strictly_increasing": bool(np.all(np.diff(primes) > 0)),
        "unique": bool(len(np.unique(primes)) == len(primes)),
        "numpy_sieve_match": bool(np.array_equal(primes, expected)),
        "independent_segmented_sieve_match": bool(np.array_equal(primes, segmented)),
        "ordinal_continuity": bool(
            arrays["ordinal"][0] == base_count + 1
            and arrays["ordinal"][-1] == base_count + len(primes)
        ),
        "residue_6_valid": bool(np.array_equal(arrays["residue_6"], primes % 6)),
        "residue_30_valid": bool(np.array_equal(arrays["residue_30"], primes % 30)),
        "residue_210_valid": bool(np.array_equal(arrays["residue_210"], primes % 210)),
        "wheel30_valid": bool(np.all((arrays["wheel30_class"] <= 7) | (arrays["wheel30_class"] == 255))),
    }
    return {"valid": all(checks.values()), "checks": checks, "candidate_prime_count": len(primes)}


def write_handoff(path: Path, summary: dict) -> None:
    shard = summary["candidate_manifest"]["shards"][0]
    checks = summary["verification"]["checks"]
    content = (
        f"# MMRF Prime Expansion Handoff — {summary['as_of']}\n\n"
        "Status: `CANDIDATE_UNPROMOTED`\n\n"
        "## Completed unit\n\n"
        f"- Range: `[{summary['range_start']:,}, {summary['range_end_exclusive']:,})`\n"
        f"- Base generation: `{summary['base_generation']}`\n"
        f"- Candidate generation: `{summary['candidate_generation']}`\n"
        f"- New primes: `{summary['prime_count_increment']:,}`\n"
        f"- Shard index: `{shard['shard_index']}`\n"
        f"- Logical CID: `{shard['cid']}`\n"
        f"- Candidate manifest SHA-256: `{summary['candidate_manifest']['manifest_sha256']}`\n\n"
        + (
            f"- Prior candidate manifest SHA-256: `{summary['candidate_manifest']['prior_candidate_manifest_sha256']}`\n\n"
            if "prior_candidate_manifest_sha256" in summary["candidate_manifest"]
            else ""
        )
        + "## Verification\n\n"
        + "\n".join(f"- {name}: `{value}`" for name, value in checks.items())
        + "\n\n## Next relay\n\n"
        "1. Re-run this workflow independently and compare the logical CID.\n"
        "2. Inspect the candidate shard and candidate manifest without changing the frozen v1.0 data.\n"
        "3. Add an independent math/data review before any promotion proposal.\n"
        "4. Do not publish this candidate as a stable generation until the governance chain is complete.\n"
    )
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--limit-exclusive", type=int, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--continue-from", type=Path, default=None)
    args = parser.parse_args()

    manifest_path = ROOT / "stable_data" / "stable_manifest_v1.0.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base_validation = validate_stable_dataset_manifest(
        manifest,
        project_root=ROOT,
        verify_shards=True,
    )
    if not base_validation["valid"]:
        raise SystemExit(f"stable_base_invalid:{json.dumps(base_validation, sort_keys=True)}")

    base_limit = int(manifest["limit_exclusive"])
    shard_size = int(manifest["shard_size"])
    prior_candidate = None
    prior_primes = np.asarray([], dtype=np.int64)
    if args.continue_from:
        prior_candidate, prior_primes = load_prior_candidate(args.continue_from, manifest)
        base_limit = int(prior_candidate["range_end_exclusive"])
        candidate_generation = int(prior_candidate["candidate_generation"]) + 1
        limit_exclusive = args.limit_exclusive or (base_limit + shard_size)
        if limit_exclusive != base_limit + shard_size:
            raise SystemExit("continued_candidate_must_be_one_shard_beyond_prior_candidate")
    else:
        candidate_generation = int(manifest["generation"]) + 1
        limit_exclusive = args.limit_exclusive or (base_limit + shard_size)
        if limit_exclusive != base_limit + shard_size:
            raise SystemExit("first_candidate_must_be_one_shard_beyond_stable_limit")

    output_dir = args.output_dir or ROOT / "research_candidates" / (
        f"{args.as_of}-generation-{candidate_generation:03d}-"
        f"{base_limit}-{limit_exclusive}"
    )
    output_dir = output_dir.resolve()
    try:
        output_dir.relative_to(ROOT)
    except ValueError as exc:
        raise SystemExit("output_dir_must_be_inside_project_root") from exc
    shard_dir = output_dir / "shards"
    shard_dir.mkdir(parents=True, exist_ok=True)

    stable_primes = load_stable_primes(manifest)
    prior_primes = prior_primes.astype(np.int64, copy=False)
    known_primes = np.concatenate([stable_primes, prior_primes])
    all_primes = numpy_sieve(limit_exclusive)
    if prior_candidate is not None:
        prior_expected = all_primes[
            np.searchsorted(all_primes, int(prior_candidate["range_start"]), side="left"):
            np.searchsorted(all_primes, int(prior_candidate["range_end_exclusive"]), side="left")
        ]
        if not np.array_equal(prior_primes, prior_expected):
            raise SystemExit("prior_candidate_prime_values_mismatch")
    arrays = build_candidate_arrays(
        all_primes,
        len(known_primes),
        base_limit,
        limit_exclusive,
    )
    verification = verify_arrays(
        arrays,
        all_primes,
        len(known_primes),
        base_limit,
        limit_exclusive,
    )
    if not verification["valid"]:
        raise SystemExit(f"candidate_arrays_invalid:{json.dumps(verification, sort_keys=True)}")

    content_sha = canonical_array_content_sha256(arrays)
    shard_index = int(manifest["shard_count"]) + (1 if prior_candidate is not None else 0)
    shard_path = shard_dir / f"shard_{shard_index:06d}_{content_sha[:16]}.npz"
    if not shard_path.exists():
        np.savez_compressed(shard_path, **arrays)
    file_sha = file_sha256(shard_path)
    shard_record = {
        "shard_index": shard_index,
        "cid": f"mmrf-shard:{content_sha}",
        "range_start": base_limit,
        "range_end_exclusive": limit_exclusive,
        "row_count": len(arrays["prime"]),
        "file_path": str(shard_path.relative_to(ROOT)).replace("\\", "/"),
        "file_sha256": file_sha,
        "content_sha256": content_sha,
    }
    candidate_core = {
        "schema": "mmrf-prime-expansion-candidate-1.0",
        "candidate_id": f"mmrf-expansion-{args.as_of}-{base_limit}-{limit_exclusive}",
        "status": "CANDIDATE_UNPROMOTED",
        "dataset_id": manifest["dataset_id"],
        "base_manifest_sha256": manifest["manifest_sha256"],
        "base_generation": int(manifest["generation"]),
        "candidate_generation": candidate_generation,
        "range_start": base_limit,
        "range_end_exclusive": limit_exclusive,
        "shard_size": shard_size,
        "shard_count_increment": 1,
        "prime_count_increment": len(arrays["prime"]),
        "column_order": list(V09_COLUMNS),
        "cid_semantics": manifest["cid_semantics"],
        "safety": manifest["safety"],
        "shards": [shard_record],
        "required_review": [
            "independent_math_validation",
            "independent_data_integrity_validation",
        ],
        "created_on": args.as_of,
    }
    if prior_candidate is not None:
        candidate_core.update({
            "prior_candidate_id": prior_candidate["candidate_id"],
            "prior_candidate_manifest_sha256": prior_candidate["manifest_sha256"],
            "prior_candidate_generation": int(prior_candidate["candidate_generation"]),
        })
    candidate_manifest = {
        **candidate_core,
        "manifest_sha256": sha256_json(candidate_core),
    }
    verification_record = {
        "schema": "mmrf-prime-expansion-verification-1.0",
        "candidate_id": candidate_core["candidate_id"],
        "base_manifest_sha256": manifest["manifest_sha256"],
        "candidate_manifest_sha256": candidate_manifest["manifest_sha256"],
        "base_manifest_validation": base_validation,
        "verification": verification,
        "logical_content_sha256": content_sha,
        "transport_file_sha256": file_sha,
        "prior_stable_shards_untouched": True,
        "verified_on": args.as_of,
    }
    if prior_candidate is not None:
        verification_record["prior_candidate_id"] = prior_candidate["candidate_id"]
        verification_record["prior_candidate_manifest_sha256"] = prior_candidate["manifest_sha256"]
        verification_record["prior_candidate_prime_count"] = len(prior_primes)
    verification_record["verification_sha256"] = sha256_json(verification_record)
    (output_dir / "candidate_manifest.json").write_text(
        json.dumps(candidate_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "verification.json").write_text(
        json.dumps(verification_record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = {
        "as_of": args.as_of,
        "base_generation": int(manifest["generation"]),
        "candidate_generation": candidate_generation,
        "range_start": base_limit,
        "range_end_exclusive": limit_exclusive,
        "prime_count_increment": len(arrays["prime"]),
        "candidate_manifest": candidate_manifest,
        "verification": verification,
    }
    if prior_candidate is not None:
        summary["prior_candidate_manifest_sha256"] = prior_candidate["manifest_sha256"]
    write_handoff(output_dir / "HANDOFF.md", summary)
    print(json.dumps({
        "status": candidate_core["status"],
        "candidate_id": candidate_core["candidate_id"],
        "range": [base_limit, limit_exclusive],
        "prime_count_increment": len(arrays["prime"]),
        "logical_content_sha256": content_sha,
        "transport_file_sha256": file_sha,
        "candidate_manifest_sha256": candidate_manifest["manifest_sha256"],
        "verification_sha256": verification_record["verification_sha256"],
        "output_dir": str(output_dir),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
