from __future__ import annotations

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "realmapbench-v1.json"
TRUTH_PATH = ROOT / "data" / "realmapbench-v1.truth.json"
MANIFEST_PATH = ROOT / "data" / "realmapbench-v1.manifest.json"


def test_validator_rejects_a_truth_sidecar_with_a_missing_case(tmp_path: Path):
    from realmapbench.dataset import validate_release

    truth = json.loads(TRUTH_PATH.read_text(encoding="utf-8"))
    truth["snapshots"].pop()
    bad_truth_path = tmp_path / "truth.json"
    bad_truth_path.write_text(
        json.dumps(truth, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="exactly 72 valid snapshots"):
        validate_release(DATASET_PATH, bad_truth_path, manifest_path=None)


def test_validator_accepts_the_published_release():
    from realmapbench.dataset import validate_release

    summary = validate_release(DATASET_PATH, TRUTH_PATH, MANIFEST_PATH)

    assert summary == {
        "dataset_revision": "realmapbench-v1-public-72-r2",
        "truth_snapshot_id": "truth-realmapbench-v1-public-72-r2",
        "case_count": 72,
    }


def test_validator_rejects_coordinated_noncanonical_snapshot_ids(tmp_path: Path):
    from realmapbench.dataset import validate_release

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    truth = json.loads(TRUTH_PATH.read_text(encoding="utf-8"))
    dataset["cases"][0]["truth"]["snapshot_id"] = "truth-realmapbench-v1/wrong"
    truth["snapshots"][0]["snapshot_id"] = "truth-realmapbench-v1/wrong"
    bad_dataset_path = tmp_path / "dataset.json"
    bad_truth_path = tmp_path / "truth.json"
    bad_dataset_path.write_text(
        json.dumps(dataset, ensure_ascii=False),
        encoding="utf-8",
    )
    bad_truth_path.write_text(
        json.dumps(truth, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="canonical snapshot ID"):
        validate_release(bad_dataset_path, bad_truth_path, manifest_path=None)
