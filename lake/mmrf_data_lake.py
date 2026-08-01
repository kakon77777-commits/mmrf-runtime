from __future__ import annotations

import hashlib
import json
import math
import random
import shutil
import sqlite3
import statistics
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import numpy as np


COLUMN_ORDER = (
    "prime",
    "ordinal",
    "bit_length",
    "decimal_digits",
    "previous_gap",
    "residue_6",
    "residue_30",
    "residue_210",
    "family_flags",
)

# Bit masks for the `family_flags` column. Each is set on the LARGER member of
# the pair, which is what lets an append leave every prior shard untouched.
#
# There is deliberately no `sophie_germain_relation` entry. It used to be here
# with mask 8 — the same mask as `safe_prime` — while `_shard_arrays` never set
# a Sophie Germain bit at all. Because `_aggregates` derives `family_counts` by
# iterating this mapping, the surface reported the safe-prime count a second
# time under a Sophie Germain label: a real quantity, a plausible magnitude, and
# the wrong one.
#
# Concretely, over [0, 2_000_000) it answered 7746. That is the count of Sophie
# Germain primes p whose partner 2p+1 also lands inside the range — the same
# pairs the safe-prime bit already counts, recorded at the other member. The
# number of Sophie Germain primes below 2_000_000 is 13934. Both readings are
# defensible from the name, which is exactly the problem: the caller cannot tell
# which one they were handed, and neither can this mapping.
#
# The column cannot simply gain a bit 16: the generation-2 dataset is frozen and
# its shard bytes are covered by the signed stable manifest. Encoding a new
# family means a new generation, which is an append, not an edit. Until then the
# honest surface is four families — the four the column actually carries.
FAMILY_BITS = {
    "twin_prime": 1,
    "cousin_prime": 2,
    "sexy_prime": 4,
    "safe_prime": 8,
}

ALLOWED_OPERATIONS = {
    "dataset_metadata",
    "interval_density",
    "gap_quantiles",
    "gap_histogram",
    "residue_distribution",
    "family_counts",
    "workflow_replay",
}

ALLOWED_MODULI = {6, 30, 210}
ALLOWED_QUANTILES = {0.5, 0.9, 0.95, 0.99}

FORBIDDEN_QUERY_FIELDS = {
    "n",
    "integer",
    "target",
    "modulus",
    "rsa_modulus",
    "public_key",
    "private_key",
    "factor",
    "factors",
    "candidate",
    "candidates",
    "range_narrowing",
    "nearest_prime",
    "prime_list",
    "exact_primes",
    "source_integer",
    "source_factor_relation",
}

QUERY_COST = {
    "dataset_metadata": 1,
    "interval_density": 2,
    "gap_quantiles": 5,
    "gap_histogram": 5,
    "residue_distribution": 4,
    "family_counts": 3,
    "workflow_replay": 10,
}


class EmptyShardSelection(LookupError):
    """Raised when a shard-range query resolves to no registered shards.

    Distinct from "this range contains no primes", which is a real aggregate
    result. This means the index cannot answer the question at all.
    """


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sieve(limit_exclusive: int) -> np.ndarray:
    if limit_exclusive <= 2:
        return np.array([], dtype=np.int64)
    flags = np.ones(limit_exclusive, dtype=np.bool_)
    flags[:2] = False
    maximum = math.isqrt(limit_exclusive - 1)
    for value in range(2, maximum + 1):
        if flags[value]:
            flags[value * value:limit_exclusive:value] = False
    return np.flatnonzero(flags).astype(np.int64)


def array_content_sha256(arrays: Mapping[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    digest.update(b"MMRF-NPZ-COLUMNAR-0.8\0")
    for name in COLUMN_ORDER:
        array = np.ascontiguousarray(arrays[name])
        digest.update(name.encode("utf-8") + b"\0")
        digest.update(str(array.dtype).encode("ascii") + b"\0")
        digest.update(canonical_json(list(array.shape)).encode("ascii"))
        digest.update(b"\0")
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


@dataclass
class QueryDecision:
    allowed: bool
    decision: str
    reasons: list[str]
    cost_units: int
    remaining_budget: int
    normalized_request: Optional[dict]

    def as_dict(self) -> dict:
        return asdict(self)


class ScientificQueryGuard:
    def __init__(
        self,
        *,
        shard_count: int,
        default_budget: int = 120,
        max_shards_per_query: int = 20,
    ):
        self.shard_count = int(shard_count)
        self.default_budget = int(default_budget)
        self.max_shards_per_query = int(max_shards_per_query)
        self.spend: dict[str, int] = {}
        self.shapes: dict[str, set[str]] = {}

    def _deny(
        self,
        session_id: str,
        reasons: list[str],
        cost_units: int = 0,
    ) -> QueryDecision:
        spent = self.spend.get(session_id, 0)
        return QueryDecision(
            False,
            "DENY",
            reasons,
            cost_units,
            max(0, self.default_budget - spent),
            None,
        )

    def evaluate(
        self,
        request: Mapping[str, Any],
        *,
        session_id: str,
    ) -> QueryDecision:
        if not isinstance(request, Mapping):
            return self._deny(session_id, ["request_must_be_object"])

        forbidden = sorted(set(request) & FORBIDDEN_QUERY_FIELDS)
        if forbidden:
            return self._deny(
                session_id,
                [
                    "target_conditioned_or_factor_related_field_forbidden",
                    *[f"forbidden_field:{key}" for key in forbidden],
                ],
            )

        operation = request.get("operation")
        if operation not in ALLOWED_OPERATIONS:
            return self._deny(
                session_id,
                ["operation_not_in_scientific_allowlist"],
            )
        if request.get("version") != "MMRF-SQL-0.8":
            return self._deny(session_id, ["unsupported_query_version"])

        allowed_fields = {
            "version",
            "operation",
            "shard_start",
            "shard_count",
            "modulo",
            "quantiles",
            "gap_max",
            "workflow_id",
        }
        unknown = sorted(set(request) - allowed_fields)
        if unknown:
            return self._deny(
                session_id,
                [f"unknown_field:{key}" for key in unknown],
            )

        normalized: dict[str, Any] = {
            "version": "MMRF-SQL-0.8",
            "operation": operation,
        }

        if operation not in {"dataset_metadata", "workflow_replay"}:
            start = request.get("shard_start")
            count = request.get("shard_count")
            if not isinstance(start, int) or not isinstance(count, int):
                return self._deny(
                    session_id,
                    ["shard_start_and_shard_count_must_be_integers"],
                )
            if start < 0 or count < 1:
                return self._deny(session_id, ["invalid_shard_range"])
            if count > self.max_shards_per_query:
                return self._deny(
                    session_id,
                    ["shard_count_exceeds_public_limit"],
                )
            if start + count > self.shard_count:
                return self._deny(
                    session_id,
                    ["shard_range_out_of_dataset"],
                )
            normalized["shard_start"] = start
            normalized["shard_count"] = count

        if operation == "residue_distribution":
            modulo = request.get("modulo")
            if modulo not in ALLOWED_MODULI:
                return self._deny(
                    session_id,
                    ["modulo_not_in_public_allowlist"],
                )
            normalized["modulo"] = modulo

        if operation == "gap_quantiles":
            quantiles = request.get("quantiles", [0.5, 0.9, 0.99])
            if (
                not isinstance(quantiles, list)
                or not quantiles
                or any(float(value) not in ALLOWED_QUANTILES for value in quantiles)
            ):
                return self._deny(
                    session_id,
                    ["quantiles_not_in_public_allowlist"],
                )
            normalized["quantiles"] = sorted(set(float(v) for v in quantiles))

        if operation == "gap_histogram":
            gap_max = request.get("gap_max", 256)
            if not isinstance(gap_max, int) or not (16 <= gap_max <= 2048):
                return self._deny(
                    session_id,
                    ["gap_max_out_of_range"],
                )
            normalized["gap_max"] = gap_max

        if operation == "workflow_replay":
            workflow_id = request.get("workflow_id")
            if not isinstance(workflow_id, str) or not workflow_id:
                return self._deny(session_id, ["workflow_id_required"])
            normalized["workflow_id"] = workflow_id

        cost = QUERY_COST[operation]
        if "shard_count" in normalized:
            cost += math.ceil(normalized["shard_count"] / 4)
        spent = self.spend.get(session_id, 0)
        shape = sha256_json(normalized)
        shapes = self.shapes.setdefault(session_id, set())
        if shape in shapes and operation != "dataset_metadata":
            cost *= 2
        if spent + cost > self.default_budget:
            return self._deny(
                session_id,
                ["session_query_budget_exhausted"],
                cost,
            )

        self.spend[session_id] = spent + cost
        shapes.add(shape)
        return QueryDecision(
            True,
            "ALLOW",
            ["aggregate_scientific_query"],
            cost,
            self.default_budget - self.spend[session_id],
            normalized,
        )


class DataLake:
    def __init__(
        self,
        *,
        root_dir: Path,
        index_db: Path,
        shard_size: int = 100_000,
    ):
        self.root_dir = Path(root_dir)
        self.shard_dir = self.root_dir / "shards"
        self.manifest_dir = self.root_dir.parent / "manifests"
        self.index_db = Path(index_db)
        self.shard_size = int(shard_size)
        self.shard_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        self.index_db.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.index_db)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.init_schema()

    def close(self) -> None:
        self.conn.close()

    def init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS dataset_versions(
                generation INTEGER PRIMARY KEY,
                limit_exclusive INTEGER NOT NULL,
                shard_count INTEGER NOT NULL,
                prime_count INTEGER NOT NULL,
                manifest_sha256 TEXT NOT NULL UNIQUE,
                previous_manifest_sha256 TEXT NOT NULL,
                manifest_path TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS shards(
                shard_index INTEGER PRIMARY KEY,
                generation INTEGER NOT NULL,
                cid TEXT NOT NULL UNIQUE,
                range_start INTEGER NOT NULL,
                range_end_exclusive INTEGER NOT NULL,
                row_count INTEGER NOT NULL,
                min_prime INTEGER,
                max_prime INTEGER,
                file_path TEXT NOT NULL,
                file_sha256 TEXT NOT NULL,
                content_sha256 TEXT NOT NULL UNIQUE,
                aggregate_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS query_events(
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                previous_hash_sha256 TEXT NOT NULL,
                event_hash_sha256 TEXT NOT NULL UNIQUE,
                session_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                operation TEXT,
                request_sha256 TEXT NOT NULL,
                result_sha256 TEXT,
                detail_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS workflow_runs(
                run_id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                dataset_manifest_sha256 TEXT NOT NULL,
                workflow_sha256 TEXT NOT NULL,
                output_sha256 TEXT NOT NULL,
                output_json TEXT NOT NULL,
                replay_of_run_id TEXT,
                reproducible INTEGER,
                created_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def current_version(self) -> Optional[dict]:
        row = self.conn.execute(
            """
            SELECT * FROM dataset_versions
            ORDER BY generation DESC LIMIT 1
            """
        ).fetchone()
        return dict(row) if row else None

    def shards(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM shards ORDER BY shard_index"
        )
        result = []
        for row in rows:
            item = dict(row)
            item["aggregate"] = json.loads(item.pop("aggregate_json"))
            result.append(item)
        return result

    def _build_arrays(
        self,
        primes: np.ndarray,
        prime_set: set[int],
        start: int,
        end: int,
    ) -> dict[str, np.ndarray]:
        left = int(np.searchsorted(primes, start, side="left"))
        right = int(np.searchsorted(primes, end, side="left"))
        shard_primes = primes[left:right]
        ordinals = np.arange(left + 1, right + 1, dtype=np.int64)

        previous_gap = np.zeros(len(shard_primes), dtype=np.uint32)
        if len(shard_primes):
            if left > 0:
                previous_gap[0] = int(shard_primes[0] - primes[left - 1])
            if len(shard_primes) > 1:
                previous_gap[1:] = np.diff(shard_primes).astype(np.uint32)

        bit_length = np.fromiter(
            (int(value).bit_length() for value in shard_primes),
            dtype=np.uint8,
            count=len(shard_primes),
        )
        decimal_digits = np.fromiter(
            (len(str(int(value))) for value in shard_primes),
            dtype=np.uint8,
            count=len(shard_primes),
        )

        flags = np.zeros(len(shard_primes), dtype=np.uint8)
        for index, value in enumerate(shard_primes):
            prime = int(value)
            mask = 0
            if prime - 2 in prime_set:
                mask |= FAMILY_BITS["twin_prime"]
            if prime - 4 in prime_set:
                mask |= FAMILY_BITS["cousin_prime"]
            if prime - 6 in prime_set:
                mask |= FAMILY_BITS["sexy_prime"]
            if prime > 2 and (prime - 1) % 2 == 0 and (prime - 1) // 2 in prime_set:
                mask |= FAMILY_BITS["safe_prime"]
            flags[index] = mask

        return {
            "prime": shard_primes.astype(np.int64),
            "ordinal": ordinals,
            "bit_length": bit_length,
            "decimal_digits": decimal_digits,
            "previous_gap": previous_gap,
            "residue_6": (shard_primes % 6).astype(np.uint8),
            "residue_30": (shard_primes % 30).astype(np.uint8),
            "residue_210": (shard_primes % 210).astype(np.uint16),
            "family_flags": flags,
        }

    @staticmethod
    def _aggregates(
        arrays: Mapping[str, np.ndarray],
        start: int,
        end: int,
    ) -> dict:
        row_count = len(arrays["prime"])
        gaps = arrays["previous_gap"]
        nonzero_gaps = gaps[gaps > 0]
        family_flags = arrays["family_flags"]
        return {
            "range_start": start,
            "range_end_exclusive": end,
            "width": end - start,
            "prime_count": row_count,
            "density": row_count / (end - start),
            "min_prime": int(arrays["prime"][0]) if row_count else None,
            "max_prime": int(arrays["prime"][-1]) if row_count else None,
            "gap_count": int(len(nonzero_gaps)),
            "gap_sum": int(nonzero_gaps.sum()) if len(nonzero_gaps) else 0,
            "gap_max": int(nonzero_gaps.max()) if len(nonzero_gaps) else 0,
            "family_counts": {
                name: int(np.count_nonzero(family_flags & bit))
                for name, bit in FAMILY_BITS.items()
            },
            "residue_counts": {
                str(modulo): {
                    str(int(value)): int(count)
                    for value, count in zip(*np.unique(
                        arrays[f"residue_{modulo}"],
                        return_counts=True,
                    ))
                }
                for modulo in (6, 30, 210)
            },
        }

    def append_generation(
        self,
        *,
        limit_exclusive: int,
        generation: int,
    ) -> dict:
        current = self.current_version()
        current_limit = int(current["limit_exclusive"]) if current else 0
        expected_generation = 1 if current is None else int(current["generation"]) + 1
        if generation != expected_generation:
            raise ValueError("generation_not_monotonic")
        if limit_exclusive <= current_limit:
            raise ValueError("limit_must_increase")

        started = time.perf_counter()
        primes = sieve(limit_exclusive)
        prime_set = set(int(value) for value in primes)
        existing_shards = self.shards()
        existing_hashes = {
            shard["shard_index"]: shard["file_sha256"]
            for shard in existing_shards
        }
        first_new_shard = math.ceil(current_limit / self.shard_size)
        final_shard = math.ceil(limit_exclusive / self.shard_size)

        created = []
        raw_bytes = 0
        compressed_bytes = 0
        for shard_index in range(first_new_shard, final_shard):
            start = shard_index * self.shard_size
            end = min(limit_exclusive, (shard_index + 1) * self.shard_size)
            arrays = self._build_arrays(primes, prime_set, start, end)
            content_sha = array_content_sha256(arrays)
            cid = f"mmrf-shard:{content_sha}"
            filename = f"shard_{shard_index:06d}_{content_sha[:16]}.npz"
            path = self.shard_dir / filename
            np.savez_compressed(path, **arrays)
            file_hash = file_sha256(path)
            aggregate = self._aggregates(arrays, start, end)
            created_at = utc_now()
            raw_size = sum(array.nbytes for array in arrays.values())
            raw_bytes += raw_size
            compressed_bytes += path.stat().st_size
            self.conn.execute(
                """
                INSERT INTO shards(
                    shard_index, generation, cid,
                    range_start, range_end_exclusive,
                    row_count, min_prime, max_prime,
                    file_path, file_sha256, content_sha256,
                    aggregate_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    shard_index,
                    generation,
                    cid,
                    start,
                    end,
                    len(arrays["prime"]),
                    aggregate["min_prime"],
                    aggregate["max_prime"],
                    str(path.relative_to(self.root_dir.parent.parent)),
                    file_hash,
                    content_sha,
                    canonical_json(aggregate),
                    created_at,
                ),
            )
            created.append({
                "shard_index": shard_index,
                "cid": cid,
                "range_start": start,
                "range_end_exclusive": end,
                "row_count": len(arrays["prime"]),
                "file_path": str(path),
                "file_sha256": file_hash,
                "content_sha256": content_sha,
                "raw_bytes": raw_size,
                "compressed_bytes": path.stat().st_size,
            })

        all_shards = self.shards()
        previous_manifest = (
            current["manifest_sha256"] if current else "0" * 64
        )
        manifest_core = {
            "schema": "mmrf-data-lake-manifest-0.8",
            "dataset_id": "mmrf-public-prime-lake",
            "generation": generation,
            "limit_exclusive": limit_exclusive,
            "shard_size": self.shard_size,
            "shard_count": len(all_shards),
            "prime_count": int(len(primes)),
            "columnar_format": "NPZ_COMPRESSED_COLUMNS",
            "column_order": list(COLUMN_ORDER),
            "previous_manifest_sha256": previous_manifest,
            "shards": [
                {
                    "shard_index": shard["shard_index"],
                    "cid": shard["cid"],
                    "range_start": shard["range_start"],
                    "range_end_exclusive": shard["range_end_exclusive"],
                    "row_count": shard["row_count"],
                    "file_path": shard["file_path"],
                    "file_sha256": shard["file_sha256"],
                    "content_sha256": shard["content_sha256"],
                }
                for shard in all_shards
            ],
            "safety": {
                "classification": "L0_PUBLIC_MATH",
                "source_factor_relations": False,
                "rsa_target_endpoint": False,
                "factor_candidate_endpoint": False,
                "exact_prime_list_endpoint": False,
            },
            "created_at": utc_now(),
        }
        manifest = {
            **manifest_core,
            "manifest_sha256": sha256_json(manifest_core),
        }
        manifest_path = self.manifest_dir / (
            f"manifest_generation_{generation:03d}.json"
        )
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        current_path = self.manifest_dir / "current_manifest.json"
        shutil.copy2(manifest_path, current_path)

        self.conn.execute(
            """
            INSERT INTO dataset_versions(
                generation, limit_exclusive, shard_count,
                prime_count, manifest_sha256,
                previous_manifest_sha256, manifest_path,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                generation,
                limit_exclusive,
                len(all_shards),
                len(primes),
                manifest["manifest_sha256"],
                previous_manifest,
                str(manifest_path.relative_to(self.root_dir.parent.parent)),
                manifest["created_at"],
            ),
        )
        self.conn.commit()

        existing_unchanged = all(
            file_sha256(
                self.root_dir.parent.parent / all_shards[index]["file_path"]
            ) == expected
            for index, expected in existing_hashes.items()
        )
        return {
            "generation": generation,
            "limit_exclusive": limit_exclusive,
            "prime_count": len(primes),
            "created_shards": created,
            "total_shards": len(all_shards),
            "manifest": manifest,
            "manifest_path": str(manifest_path),
            "build_seconds": time.perf_counter() - started,
            "new_raw_bytes": raw_bytes,
            "new_compressed_bytes": compressed_bytes,
            "compression_ratio": (
                raw_bytes / compressed_bytes if compressed_bytes else None
            ),
            "prior_shards_unchanged": existing_unchanged,
        }

    def current_manifest(self) -> dict:
        path = self.manifest_dir / "current_manifest.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def verify_manifest_chain(self) -> dict:
        rows = list(self.conn.execute(
            "SELECT * FROM dataset_versions ORDER BY generation"
        ))
        previous = "0" * 64
        checked = 0
        for row in rows:
            path = self.root_dir.parent.parent / row["manifest_path"]
            manifest = json.loads(path.read_text(encoding="utf-8"))
            core = {
                key: value
                for key, value in manifest.items()
                if key != "manifest_sha256"
            }
            if manifest["manifest_sha256"] != sha256_json(core):
                return {
                    "valid": False,
                    "generation": row["generation"],
                    "reason": "manifest_hash_mismatch",
                }
            if manifest["previous_manifest_sha256"] != previous:
                return {
                    "valid": False,
                    "generation": row["generation"],
                    "reason": "manifest_chain_mismatch",
                }
            previous = manifest["manifest_sha256"]
            checked += 1
        return {
            "valid": True,
            "generations": checked,
            "head_manifest_sha256": previous,
        }

    def verify_shard(
        self,
        shard: Mapping[str, Any],
        *,
        base_dir: Optional[Path] = None,
    ) -> dict:
        if base_dir is None:
            path = self.root_dir.parent.parent / shard["file_path"]
        else:
            path = (
                Path(base_dir)
                / "shards"
                / Path(shard["file_path"]).name
            )
        if not path.exists():
            return {
                "valid": False,
                "shard_index": shard["shard_index"],
                "reason": "shard_missing",
            }
        file_hash = file_sha256(path)
        if file_hash != shard["file_sha256"]:
            return {
                "valid": False,
                "shard_index": shard["shard_index"],
                "reason": "file_hash_mismatch",
            }
        try:
            with np.load(path, allow_pickle=False) as loaded:
                arrays = {name: loaded[name] for name in COLUMN_ORDER}
        except Exception as exc:
            return {
                "valid": False,
                "shard_index": shard["shard_index"],
                "reason": f"npz_load_error:{type(exc).__name__}",
            }
        lengths = {len(array) for array in arrays.values()}
        content_hash = array_content_sha256(arrays)
        checks = {
            "column_lengths_equal": len(lengths) == 1,
            "row_count_ok": lengths == {int(shard["row_count"])},
            "content_hash_ok": content_hash == shard["content_sha256"],
            "cid_ok": shard["cid"] == f"mmrf-shard:{content_hash}",
            "prime_sorted": bool(
                len(arrays["prime"]) < 2
                or np.all(arrays["prime"][1:] > arrays["prime"][:-1])
            ),
        }
        return {
            "valid": all(checks.values()),
            "shard_index": shard["shard_index"],
            "checks": checks,
            "reason": None if all(checks.values()) else "shard_integrity_mismatch",
        }

    def integrity_sample(
        self,
        *,
        sample_count: int,
        seed: int,
        base_dir: Optional[Path] = None,
        forced_indices: Optional[Sequence[int]] = None,
    ) -> dict:
        shards = self.shards()
        if forced_indices is None:
            rng = random.Random(seed)
            selected = sorted(
                rng.sample(
                    [shard["shard_index"] for shard in shards],
                    min(sample_count, len(shards)),
                )
            )
        else:
            selected = sorted(set(int(value) for value in forced_indices))
        shard_map = {shard["shard_index"]: shard for shard in shards}
        results = [
            self.verify_shard(shard_map[index], base_dir=base_dir)
            for index in selected
        ]
        return {
            "valid": all(result["valid"] for result in results),
            "sample_count": len(selected),
            "seed": seed,
            "selected_indices": selected,
            "results": results,
        }

    def mirror_to(self, mirror_root: Path) -> dict:
        mirror_root = Path(mirror_root)
        if mirror_root.exists():
            shutil.rmtree(mirror_root)
        mirror_root.mkdir(parents=True, exist_ok=True)
        copied = 0
        for shard in self.shards():
            source = self.root_dir.parent.parent / shard["file_path"]
            target = mirror_root / "shards" / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied += 1
        return {
            "copied_shards": copied,
            "mirror_root": str(mirror_root),
        }

    def _selected_shards(
        self,
        start: int,
        count: int,
    ) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT * FROM shards
            WHERE shard_index >= ? AND shard_index < ?
            ORDER BY shard_index
            """,
            (start, start + count),
        )
        result = []
        for row in rows:
            item = dict(row)
            item["aggregate"] = json.loads(item.pop("aggregate_json"))
            result.append(item)
        if not result:
            # An aggregate over nothing is not an aggregate of zero. The index
            # is built on append, so an empty selection means the requested
            # shards are not registered here — a missing index reads exactly
            # like a range that legitimately holds no primes.
            #
            # Without this guard the four shipped operations fail four
            # different ways: interval_density raises IndexError on shards[0],
            # gap_quantiles and residue_distribution raise ValueError inside
            # np.concatenate, and family_counts returns status OK with every
            # count at zero and files_opened at zero. The last is the dangerous
            # one, because a replay of the published baseline workflow then
            # reports "0 twin primes below 2,000,000" and calls it a success.
            raise EmptyShardSelection(
                f"No shards registered for index range "
                f"[{start}, {start + count}). The lake index at "
                f"{getattr(self, 'index_database', 'lake_state/lake_index.sqlite')} "
                f"holds no matching rows; append the dataset or point "
                f"--index-database at an index that does."
            )
        return result

    def load_columns(
        self,
        shards: Sequence[Mapping[str, Any]],
        columns: Sequence[str],
        *,
        base_dir: Optional[Path] = None,
    ) -> tuple[dict[str, list[np.ndarray]], dict]:
        base = (
            Path(base_dir)
            if base_dir is not None
            else self.root_dir.parent.parent
        )
        loaded: dict[str, list[np.ndarray]] = {
            column: [] for column in columns
        }
        bytes_loaded = 0
        files_opened = 0
        started = time.perf_counter_ns()
        for shard in shards:
            path = base / shard["file_path"]
            with np.load(path, allow_pickle=False) as archive:
                for column in columns:
                    array = archive[column]
                    loaded[column].append(array)
                    bytes_loaded += array.nbytes
            files_opened += 1
        return loaded, {
            "files_opened": files_opened,
            "columns_loaded": list(columns),
            "uncompressed_column_bytes": bytes_loaded,
            "elapsed_ms": (
                time.perf_counter_ns() - started
            ) / 1_000_000,
            "index_only": False,
        }

    def _audit_root(self) -> str:
        row = self.conn.execute(
            """
            SELECT event_hash_sha256 FROM query_events
            ORDER BY sequence DESC LIMIT 1
            """
        ).fetchone()
        return row["event_hash_sha256"] if row else "0" * 64

    def _record_query(
        self,
        *,
        session_id: str,
        decision: QueryDecision,
        request: Mapping[str, Any],
        result: Optional[Mapping[str, Any]],
    ) -> dict:
        previous = self._audit_root()
        event_id = f"lake-query:{uuid.uuid4()}"
        detail = {
            "reasons": decision.reasons,
            "cost_units": decision.cost_units,
            "remaining_budget": decision.remaining_budget,
        }
        body = {
            "event_id": event_id,
            "previous_hash_sha256": previous,
            "session_id": session_id,
            "decision": decision.decision,
            "operation": (
                decision.normalized_request["operation"]
                if decision.normalized_request
                else request.get("operation")
            ),
            "request_sha256": sha256_json(request),
            "result_sha256": sha256_json(result) if result is not None else None,
            "detail": detail,
            "created_at": utc_now(),
        }
        event_hash = sha256_json(body)
        self.conn.execute(
            """
            INSERT INTO query_events(
                event_id, previous_hash_sha256,
                event_hash_sha256, session_id,
                decision, operation, request_sha256,
                result_sha256, detail_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                previous,
                event_hash,
                session_id,
                decision.decision,
                body["operation"],
                body["request_sha256"],
                body["result_sha256"],
                canonical_json(detail),
                body["created_at"],
            ),
        )
        self.conn.commit()
        return {
            "event_id": event_id,
            "event_hash_sha256": event_hash,
        }

    def execute_query(
        self,
        request: Mapping[str, Any],
        *,
        session_id: str,
        guard: ScientificQueryGuard,
        workflow_dir: Optional[Path] = None,
    ) -> dict:
        decision = guard.evaluate(request, session_id=session_id)
        if not decision.allowed:
            audit = self._record_query(
                session_id=session_id,
                decision=decision,
                request=request,
                result=None,
            )
            return {
                "schema": "mmrf-scientific-query-response-0.8",
                "status": "DENIED",
                "decision": decision.as_dict(),
                "audit": audit,
            }

        query = decision.normalized_request
        assert query is not None
        operation = query["operation"]
        scan_profile = {
            "files_opened": 0,
            "columns_loaded": [],
            "uncompressed_column_bytes": 0,
            "elapsed_ms": 0.0,
            "index_only": False,
        }

        if operation == "dataset_metadata":
            manifest = self.current_manifest()
            result = {
                key: manifest[key]
                for key in (
                    "dataset_id",
                    "generation",
                    "limit_exclusive",
                    "shard_size",
                    "shard_count",
                    "prime_count",
                    "columnar_format",
                    "column_order",
                    "manifest_sha256",
                    "safety",
                )
            }
            scan_profile["index_only"] = True

        elif operation == "interval_density":
            shards = self._selected_shards(
                query["shard_start"],
                query["shard_count"],
            )
            total_width = sum(
                shard["aggregate"]["width"] for shard in shards
            )
            total_primes = sum(
                shard["aggregate"]["prime_count"] for shard in shards
            )
            result = {
                "shard_start": query["shard_start"],
                "shard_count": query["shard_count"],
                "range_start": shards[0]["range_start"],
                "range_end_exclusive": shards[-1]["range_end_exclusive"],
                "prime_count": total_primes,
                "density": total_primes / total_width,
            }
            scan_profile["index_only"] = True

        elif operation == "gap_quantiles":
            shards = self._selected_shards(
                query["shard_start"],
                query["shard_count"],
            )
            loaded, scan_profile = self.load_columns(
                shards,
                ["previous_gap"],
            )
            values = np.concatenate(loaded["previous_gap"])
            values = values[values > 0]
            result = {
                "shard_start": query["shard_start"],
                "shard_count": query["shard_count"],
                "sample_size": int(len(values)),
                "quantiles": {
                    str(value): float(np.quantile(values, value))
                    for value in query["quantiles"]
                },
            }

        elif operation == "gap_histogram":
            shards = self._selected_shards(
                query["shard_start"],
                query["shard_count"],
            )
            loaded, scan_profile = self.load_columns(
                shards,
                ["previous_gap"],
            )
            values = np.concatenate(loaded["previous_gap"])
            values = values[(values > 0) & (values <= query["gap_max"])]
            counts = np.bincount(
                values.astype(np.int64),
                minlength=query["gap_max"] + 1,
            )
            result = {
                "shard_start": query["shard_start"],
                "shard_count": query["shard_count"],
                "gap_max": query["gap_max"],
                "histogram": [
                    {"gap": int(index), "count": int(count)}
                    for index, count in enumerate(counts)
                    if count
                ],
            }

        elif operation == "residue_distribution":
            shards = self._selected_shards(
                query["shard_start"],
                query["shard_count"],
            )
            column = f"residue_{query['modulo']}"
            loaded, scan_profile = self.load_columns(
                shards,
                [column],
            )
            values = np.concatenate(loaded[column])
            residues, counts = np.unique(values, return_counts=True)
            result = {
                "shard_start": query["shard_start"],
                "shard_count": query["shard_count"],
                "modulo": query["modulo"],
                "distribution": [
                    {"residue": int(value), "count": int(count)}
                    for value, count in zip(residues, counts)
                ],
            }

        elif operation == "family_counts":
            shards = self._selected_shards(
                query["shard_start"],
                query["shard_count"],
            )
            counts = {
                family: sum(
                    shard["aggregate"]["family_counts"][family]
                    for shard in shards
                )
                for family in FAMILY_BITS
            }
            result = {
                "shard_start": query["shard_start"],
                "shard_count": query["shard_count"],
                "counts": counts,
                "pair_indexing": (
                    "Each pair is counted at its larger observed member; "
                    "this keeps prior shards immutable during append."
                ),
            }
            scan_profile["index_only"] = True

        elif operation == "workflow_replay":
            if workflow_dir is None:
                raise ValueError("workflow_dir_required")
            result = self.replay_workflow(
                workflow_id=query["workflow_id"],
                workflow_dir=workflow_dir,
            )
            scan_profile["index_only"] = False

        else:
            raise AssertionError(operation)

        response = {
            "schema": "mmrf-scientific-query-response-0.8",
            "status": "OK",
            "query": query,
            "result": result,
            "scan_profile": scan_profile,
            "decision": decision.as_dict(),
            "safety": {
                "aggregate_only": True,
                "target_conditioned": False,
                "returns_exact_prime_list": False,
                "returns_factor_candidates": False,
                "source_factor_relations": False,
            },
        }
        response["audit"] = self._record_query(
            session_id=session_id,
            decision=decision,
            request=request,
            result=response,
        )
        return response

    def verify_query_audit(self) -> dict:
        previous = "0" * 64
        count = 0
        for row in self.conn.execute(
            "SELECT * FROM query_events ORDER BY sequence"
        ):
            detail = json.loads(row["detail_json"])
            body = {
                "event_id": row["event_id"],
                "previous_hash_sha256": previous,
                "session_id": row["session_id"],
                "decision": row["decision"],
                "operation": row["operation"],
                "request_sha256": row["request_sha256"],
                "result_sha256": row["result_sha256"],
                "detail": detail,
                "created_at": row["created_at"],
            }
            expected = sha256_json(body)
            if row["previous_hash_sha256"] != previous:
                return {
                    "valid": False,
                    "count": count,
                    "failed_sequence": row["sequence"],
                    "reason": "previous_hash_mismatch",
                }
            if row["event_hash_sha256"] != expected:
                return {
                    "valid": False,
                    "count": count,
                    "failed_sequence": row["sequence"],
                    "reason": "event_hash_mismatch",
                }
            previous = row["event_hash_sha256"]
            count += 1
        return {
            "valid": True,
            "count": count,
            "audit_root_sha256": previous,
        }

    def run_workflow(
        self,
        *,
        workflow: Mapping[str, Any],
        workflow_dir: Path,
        replay_of_run_id: Optional[str] = None,
    ) -> dict:
        workflow_dir = Path(workflow_dir)
        workflow_dir.mkdir(parents=True, exist_ok=True)
        manifest = self.current_manifest()
        workflow_id = workflow["workflow_id"]
        workflow_hash = sha256_json(workflow)
        guard = ScientificQueryGuard(
            shard_count=manifest["shard_count"],
            default_budget=10_000,
            max_shards_per_query=manifest["shard_count"],
        )
        outputs = []
        for index, step in enumerate(workflow["steps"]):
            request = {
                "version": "MMRF-SQL-0.8",
                **step["query"],
            }
            response = self.execute_query(
                request,
                session_id=f"workflow:{workflow_id}:{index}",
                guard=guard,
                workflow_dir=workflow_dir,
            )
            if response["status"] != "OK":
                raise RuntimeError(response)
            stable_scan_profile = {
                key: value
                for key, value in response["scan_profile"].items()
                if key != "elapsed_ms"
            }
            outputs.append({
                "step_id": step["step_id"],
                "query_sha256": sha256_json(request),
                "result": response["result"],
                "result_sha256": sha256_json(response["result"]),
                "scan_profile": stable_scan_profile,
            })

        output_document = {
            "schema": "mmrf-workflow-output-0.8",
            "workflow_id": workflow_id,
            "dataset_manifest_sha256": manifest["manifest_sha256"],
            "workflow_sha256": workflow_hash,
            "outputs": outputs,
        }
        output_hash = sha256_json(output_document)
        run_id = f"workflow-run:{uuid.uuid4()}"
        reproducible = None
        if replay_of_run_id:
            prior = self.conn.execute(
                "SELECT output_sha256 FROM workflow_runs WHERE run_id = ?",
                (replay_of_run_id,),
            ).fetchone()
            if prior is None:
                raise KeyError("replay_source_run_not_found")
            reproducible = prior["output_sha256"] == output_hash

        record = {
            **output_document,
            "run_id": run_id,
            "output_sha256": output_hash,
            "replay_of_run_id": replay_of_run_id,
            "reproducible": reproducible,
            "created_at": utc_now(),
        }
        path = workflow_dir / f"{run_id.replace(':', '_')}.json"
        path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.conn.execute(
            """
            INSERT INTO workflow_runs(
                run_id, workflow_id,
                dataset_manifest_sha256,
                workflow_sha256, output_sha256,
                output_json, replay_of_run_id,
                reproducible, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                workflow_id,
                manifest["manifest_sha256"],
                workflow_hash,
                output_hash,
                canonical_json(record),
                replay_of_run_id,
                None if reproducible is None else int(reproducible),
                record["created_at"],
            ),
        )
        self.conn.commit()
        return record

    def replay_workflow(
        self,
        *,
        workflow_id: str,
        workflow_dir: Path,
    ) -> dict:
        workflow_path = Path(workflow_dir) / f"{workflow_id}.workflow.json"
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        prior = self.conn.execute(
            """
            SELECT run_id FROM workflow_runs
            WHERE workflow_id = ?
            ORDER BY created_at ASC LIMIT 1
            """,
            (workflow_id,),
        ).fetchone()
        if prior is None:
            raise KeyError("workflow_has_no_prior_run")
        replay = self.run_workflow(
            workflow=workflow,
            workflow_dir=workflow_dir,
            replay_of_run_id=prior["run_id"],
        )
        return {
            "workflow_id": workflow_id,
            "replay_run_id": replay["run_id"],
            "replay_of_run_id": replay["replay_of_run_id"],
            "reproducible": replay["reproducible"],
            "output_sha256": replay["output_sha256"],
        }
