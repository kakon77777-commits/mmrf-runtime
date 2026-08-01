# Repairs applied after the v1.0 release was cut

This repository is the published `mmrf_v1_0_stable_research_infrastructure`
package plus a small number of repairs. The import is its own commit and is
byte-identical to the package, so `git diff` against it shows exactly what
changed and nothing else.

This file is not covered by `payload_checksums` in the signed release manifest,
so writing it does not alter what `verify-release` reports.

## What `verify-release` says about this repository

```
python install/mmrf.py --project-root . verify-release
```

```json
{
  "valid": false,
  "checks": {
    "signature_and_document_hash": true,
    "schema_ok": true,
    "release_id_ok": true,
    "version_ok": true,
    "safety_ok": true,
    "payload_ok": false
  }
}
```

with two `hash_mismatch` entries, for `lake/mmrf_data_lake.py` and
`lake/mmrf_lake_cli.py`.

That is the correct answer, not a problem to work around. The signed manifest
describes the released package; this tree is the released package with two files
repaired, and the check names them. The signature itself still verifies, and so
does every safety and semantic check. To verify the release exactly as published,
check out the import commit and run it there.

The stable dataset is untouched. No shard byte changed, and
`stable_data/stable_manifest_v1.0.json` still hashes to
`a5caea22a57efaac915c00dd92c655b1126e0b6d9b2b93790e48bc167733e0d1`.

## 1. `family_counts` reported a quantity the dataset does not carry

`FAMILY_BITS` in `lake/mmrf_data_lake.py` mapped `sophie_germain_relation` to
mask `8` — the same mask as `safe_prime` — while `_shard_arrays` never set a
Sophie Germain bit at all. `_aggregates` derives `family_counts` by iterating
that mapping, so every response carried the safe-prime count a second time under
a Sophie Germain label.

Over `[0, 2_000_000)` it answered **7746**. That is the count of Sophie Germain
primes whose partner `2p+1` also lands inside the range — the same pairs the
safe-prime bit already counts, recorded at the other member. The number of
Sophie Germain primes below two million is **13934**. Both readings are
defensible from the field name, which is the problem: neither the caller nor the
mapping could tell which one had been returned.

**Fix:** the entry was removed, not repaired. Adding a real bit 16 would change
the shard bytes, and those are covered by the signed stable manifest. Encoding a
new family is a new generation, which is an append, not an edit. Until then the
honest surface is the four families the column actually carries.

## 2. An empty shard selection was indistinguishable from an empty result

`_selected_shards` returned `[]` when the index held no matching rows, and the
aggregate path read that as a range that contains no primes.

Run against the released package, three of the four operations in
`workflows/prime-distribution-baseline.workflow.json` raised unhandled
`IndexError`/`ValueError`. The fourth was worse: `family_counts` returned
`status: OK`, `decision: ALLOW`, a full set of zero counts, and `files_opened: 0`.
A missing index read exactly like a genuinely empty range.

**Fix:** `EmptyShardSelection` is raised instead, and `lake/mmrf_lake_cli.py`
reports it as `status: NO_DATA` with exit code 2. All four operations now refuse
in the same legible way.

## 3. The shipped baseline workflow cannot be replayed from the shipped package

`prime-distribution-baseline` addresses the data lake by shard index, but neither
`lake_state/lake_index.sqlite` nor `lake_data/primary/shards/` is part of the
v1.0 package — those ship in v0.8 and v0.9 only. v1.0 ships the promoted
generation-2 dataset under `stable_data/shards/`, with different filenames.

**Not fixed here.** Whether v1.0 should ship the lake index, repoint the lake at
the stable shards, or mark this workflow as a v0.9-generation artifact is a
release decision.

**Worked around:** `workflows/stable_baseline.py` computes the same four
aggregates — plus a gap histogram, the mod-6 and mod-210 residue distributions,
and magnitude bands — directly from the promoted shards, with no index and no
network.

```
python workflows/stable_baseline.py --project-root . \
    --output results_v10/stable_baseline_output.json
```

It verifies the stable manifest against its own hash before reading anything,
refuses to run if the shard count or prime count disagrees with the manifest,
and stops if `family_flags` carries a bit it cannot name — so a future generation
cannot be silently under-counted the way defect 1 was. Its output is
canonicalised and self-hashed the same way the manifest is.

Results are independently confirmed against the primes themselves rather than
the flag column: twin 14871, cousin 14742, sexy 29419, safe 7746. Maximal gap
132 and density 148933/2000000 both match the range's known values, and the
magnitude bands sum to π(2×10⁶).

## 4. Documentation: the `--project-root` flag order is wrong everywhere

`README.md`, `README_V10.md` and `docs_v10/MMRF_OPERATIONS_MANUAL_1.0.md` all
document:

```
python install/mmrf.py verify-release --project-root .
```

`--project-root` is a top-level argument, declared before the subparsers, so
this exits 2 with `unrecognized arguments: --project-root .`. The working form
puts the flag first:

```
python install/mmrf.py --project-root . verify-release
python install/mmrf.py --project-root . doctor
```

**Not fixed in place.** All three documents are covered by `payload_checksums`,
and correcting a command in them would add three more `hash_mismatch` entries to
`verify-release` in exchange for a typo. The correction is recorded here and on
the verification page of mmrf.evemisslab.com instead. It belongs in the next
release, alongside the decision in defect 3.
