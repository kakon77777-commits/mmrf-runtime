"""Independent verifier for an MMRF prime expansion candidate.

This deliberately does not import the candidate generator. It uses a plain
Python trial-division base-prime list plus a segmented sieve to check the
candidate range, then recomputes the v0.9 logical content identity and all
derived columns.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
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
FAMILY_BITS = {"twin_prime": 1, "cousin_prime": 2, "sexy_prime": 4, "safe_prime": 8}
WHEEL30_CLASSES = {1: 0, 7: 1, 11: 2, 13: 3, 17: 4, 19: 5, 23: 6, 29: 7}


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


def trial_primes(limit: int) -> list[int]:
    primes: list[int] = []
    for value in range(2, limit + 1):
        if all(value % prime for prime in primes if prime * prime <= value):
            primes.append(value)
    return primes


def segmented_primes(start: int, end: int) -> np.ndarray:
    flags = bytearray(b"\x01") * (end - start)
    for prime in trial_primes(math.isqrt(end - 1)):
        first = max(prime * prime, ((start + prime - 1) // prime) * prime)
        for composite in range(first, end, prime):
            flags[composite - start] = 0
    return np.asarray(
        [start + offset for offset, flag in enumerate(flags) if flag and start + offset >= 2],
        dtype=np.int64,
    )


def logical_content_sha256(arrays: dict[str, np.ndarray]) -> str:
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


def load_base_primes(base_manifest: dict) -> np.ndarray:
    parts = []
    for record in base_manifest["shards"]:
        with np.load(ROOT / record["file_path"], allow_pickle=False) as archive:
            parts.append(np.asarray(archive["prime"], dtype=np.int64))
    return np.concatenate(parts)


def candidate_manifest_catalog() -> dict[str, Path]:
    catalog: dict[str, Path] = {}
    for manifest_path in (ROOT / "research_candidates").glob("**/candidate_manifest.json"):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_sha = manifest.get("manifest_sha256")
        if manifest_sha in catalog and catalog[manifest_sha] != manifest_path.parent:
            raise SystemExit(f"duplicate_candidate_manifest_sha256:{manifest_sha}")
        catalog[manifest_sha] = manifest_path.parent
    return catalog


def load_candidate_entry(candidate_dir: Path) -> tuple[dict, dict[str, np.ndarray]]:
    candidate_dir = candidate_dir.resolve()
    manifest = json.loads((candidate_dir / "candidate_manifest.json").read_text(encoding="utf-8"))
    review = json.loads((candidate_dir / "independent_review.json").read_text(encoding="utf-8"))
    record = manifest["shards"][0]
    with np.load(ROOT / record["file_path"], allow_pickle=False) as archive:
        if tuple(archive.files) != V09_COLUMNS:
            raise SystemExit("prior_candidate_columns_mismatch")
        arrays = {name: np.asarray(archive[name]) for name in V09_COLUMNS}
    manifest_hash_ok = manifest["manifest_sha256"] == sha256_json(
        {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    )
    if not manifest_hash_ok or manifest["status"] != "CANDIDATE_UNPROMOTED":
        raise SystemExit("prior_candidate_manifest_invalid")
    if review.get("valid") is not True or review.get("candidate_manifest_sha256") != manifest["manifest_sha256"]:
        raise SystemExit("prior_candidate_independent_review_invalid")
    if len(arrays["prime"]) != int(record["row_count"]):
        raise SystemExit("prior_candidate_row_count_mismatch")
    if file_sha256(ROOT / record["file_path"]) != record["file_sha256"]:
        raise SystemExit("prior_candidate_transport_hash_mismatch")
    if logical_content_sha256(arrays) != record["content_sha256"]:
        raise SystemExit("prior_candidate_logical_hash_mismatch")
    return manifest, arrays


def load_prior_candidate_chain(candidate_dir: Path, base: dict) -> tuple[dict, np.ndarray, list[dict]]:
    catalog = candidate_manifest_catalog()
    reverse_chain: list[tuple[dict, dict[str, np.ndarray]]] = []
    seen: set[str] = set()
    current_dir = candidate_dir.resolve()
    while True:
        manifest, arrays = load_candidate_entry(current_dir)
        manifest_sha = manifest["manifest_sha256"]
        if manifest_sha in seen:
            raise SystemExit("prior_candidate_chain_cycle")
        seen.add(manifest_sha)
        reverse_chain.append((manifest, arrays))
        prior_sha = manifest.get("prior_candidate_manifest_sha256")
        if prior_sha is None:
            break
        if prior_sha not in catalog:
            raise SystemExit(f"prior_candidate_manifest_not_found:{prior_sha}")
        current_dir = catalog[prior_sha]

    chain = list(reversed(reverse_chain))
    expected_generation = int(base["generation"]) + 1
    expected_start = int(base["limit_exclusive"])
    expected_shard_index = int(base["shard_count"])
    expected_ordinal = int(base["prime_count"]) + 1
    previous: dict | None = None
    chain_primes: list[np.ndarray] = []
    for manifest, arrays in chain:
        record = manifest["shards"][0]
        primes = np.asarray(arrays["prime"], dtype=np.int64)
        ordinals = np.asarray(arrays["ordinal"], dtype=np.int64)
        checks = (
            manifest.get("base_manifest_sha256") == base["manifest_sha256"],
            int(manifest["candidate_generation"]) == expected_generation,
            int(manifest["range_start"]) == expected_start,
            int(manifest["range_end_exclusive"]) == expected_start + int(base["shard_size"]),
            int(record["shard_index"]) == expected_shard_index,
            np.array_equal(
                ordinals,
                np.arange(expected_ordinal, expected_ordinal + len(primes), dtype=np.int64),
            ),
        )
        if not all(checks):
            raise SystemExit(
                f"prior_candidate_full_chain_invalid:generation={expected_generation}"
            )
        if previous is None:
            direct_binding_ok = "prior_candidate_manifest_sha256" not in manifest
        else:
            direct_binding_ok = (
                manifest.get("prior_candidate_manifest_sha256") == previous["manifest_sha256"]
                and int(manifest.get("prior_candidate_generation", -1))
                == int(previous["candidate_generation"])
            )
        if not direct_binding_ok:
            raise SystemExit("prior_candidate_direct_binding_invalid")
        chain_primes.append(primes)
        previous = manifest
        expected_generation += 1
        expected_start = int(manifest["range_end_exclusive"])
        expected_shard_index += 1
        expected_ordinal += len(primes)

    return chain[-1][0], np.concatenate(chain_primes), [item[0] for item in chain]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--prior-candidate-dir", type=Path, default=None)
    args = parser.parse_args()
    candidate_dir = args.candidate_dir.resolve()
    candidate = json.loads((candidate_dir / "candidate_manifest.json").read_text(encoding="utf-8"))
    base = json.loads((ROOT / "stable_data" / "stable_manifest_v1.0.json").read_text(encoding="utf-8"))
    record = candidate["shards"][0]
    shard_path = ROOT / record["file_path"]

    with np.load(shard_path, allow_pickle=False) as archive:
        arrays = {name: np.asarray(archive[name]) for name in V09_COLUMNS}
    base_primes = load_base_primes(base)
    prior_candidate = None
    prior_primes = np.asarray([], dtype=np.int64)
    prior_chain: list[dict] = []
    if args.prior_candidate_dir:
        prior_candidate, prior_primes, prior_chain = load_prior_candidate_chain(
            args.prior_candidate_dir,
            base,
        )
    elif "prior_candidate_manifest_sha256" in candidate:
        raise SystemExit("prior_candidate_dir_required_for_continued_candidate")
    known_primes = np.concatenate([base_primes, prior_primes])
    primes = arrays["prime"].astype(np.int64)
    start = int(candidate["range_start"])
    end = int(candidate["range_end_exclusive"])
    expected = segmented_primes(start, end)
    prime_set = set(int(value) for value in np.concatenate([known_primes, primes]))

    expected_flags = np.zeros(len(primes), dtype=np.uint8)
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
        expected_flags[index] = mask

    expected_gap = np.zeros(len(primes), dtype=np.uint32)
    expected_gap[0] = int(primes[0] - known_primes[-1])
    expected_gap[1:] = np.diff(primes).astype(np.uint32)
    expected_wheel = np.asarray(
        [WHEEL30_CLASSES.get(int(value % 30), 255) for value in primes],
        dtype=np.uint8,
    )
    checks = {
        "base_manifest_hash_ok": base["manifest_sha256"] == sha256_json({k: v for k, v in base.items() if k != "manifest_sha256"}),
        "candidate_manifest_hash_ok": candidate["manifest_sha256"] == sha256_json({k: v for k, v in candidate.items() if k != "manifest_sha256"}),
        "base_binding_ok": candidate["base_manifest_sha256"] == base["manifest_sha256"],
        "prior_candidate_chain_ok": bool(
            (prior_candidate is None and "prior_candidate_manifest_sha256" not in candidate)
            or (
                prior_candidate is not None
                and candidate.get("prior_candidate_manifest_sha256") == prior_candidate["manifest_sha256"]
                and candidate.get("prior_candidate_generation") == prior_candidate.get("candidate_generation")
                and start == int(prior_candidate["range_end_exclusive"])
                and int(record["shard_index"]) == int(prior_candidate["shards"][0]["shard_index"]) + 1
                and int(candidate["candidate_generation"]) == int(prior_candidate["candidate_generation"]) + 1
            )
        ),
        "status_unpromoted": candidate["status"] == "CANDIDATE_UNPROMOTED",
        "columns_exact": tuple(arrays) == V09_COLUMNS,
        "row_count_ok": len(primes) == int(record["row_count"]),
        "range_ok": bool(len(primes) and primes[0] >= start and primes[-1] < end),
        "strictly_increasing": bool(np.all(np.diff(primes) > 0)),
        "segmented_sieve_match": bool(np.array_equal(primes, expected)),
        "ordinal_continuity": bool(
            arrays["ordinal"][0] == len(known_primes) + 1
            and arrays["ordinal"][-1] == len(known_primes) + len(primes)
        ),
        "previous_gap_match": bool(np.array_equal(arrays["previous_gap"], expected_gap)),
        "family_flags_match": bool(np.array_equal(arrays["family_flags"], expected_flags)),
        "wheel30_class_match": bool(np.array_equal(arrays["wheel30_class"], expected_wheel)),
        "logical_content_hash_ok": logical_content_sha256(arrays) == record["content_sha256"],
        "transport_file_hash_ok": file_sha256(shard_path) == record["file_sha256"],
        "candidate_range_is_next_shard": (
            start == int(base["limit_exclusive"])
            if prior_candidate is None
            else start == int(prior_candidate["range_end_exclusive"])
        ) and end == start + int(base["shard_size"]),
    }
    core = {
        "schema": "mmrf-prime-expansion-independent-review-1.0",
        "candidate_id": candidate["candidate_id"],
        "candidate_manifest_sha256": candidate["manifest_sha256"],
        "shard_index": record["shard_index"],
        "range": [start, end],
        "prime_count": len(primes),
        "logical_content_sha256": record["content_sha256"],
        "prior_candidate_chain_length": len(prior_chain),
        "checks": checks,
        "valid": all(checks.values()),
    }
    review = {**core, "review_sha256": sha256_json(core)}
    (candidate_dir / "independent_review.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(review, ensure_ascii=False, indent=2))
    return 0 if review["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
