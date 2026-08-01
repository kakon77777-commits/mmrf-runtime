from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mmrf_stable.runtime import (
    FROZEN_SEMANTICS,
    plan_upgrade,
    validate_stable_dataset_manifest,
    verify_release,
)


def main() -> None:
    stable = json.loads(
        (
            ROOT / "stable_data" / "stable_manifest_v1.0.json"
        ).read_text(encoding="utf-8")
    )
    validation = validate_stable_dataset_manifest(
        stable,
        project_root=ROOT,
        verify_shards=True,
    )
    assert validation["valid"]
    assert stable["frozen_semantics"] == FROZEN_SEMANTICS
    assert stable["prime_count"] == 148_933
    assert stable["shard_count"] == 20
    assert plan_upgrade(stable)["source_version"] == "1.0"

    unsafe = copy.deepcopy(stable)
    unsafe["safety"]["rsa_target_endpoint"] = True
    assert not validate_stable_dataset_manifest(
        unsafe,
        project_root=ROOT,
        verify_shards=False,
    )["valid"]

    release = verify_release(
        release_root=ROOT,
        manifest_path=(
            ROOT
            / "release_v10"
            / "stable_release_manifest_v1.0.json"
        ),
        public_key_path=(
            ROOT
            / "release_v10"
            / "stable_release_signing.public.pem"
        ),
        verify_payload=True,
    )
    assert release["valid"]
    print("MMRF v1.0 smoke test passed")


if __name__ == "__main__":
    main()
