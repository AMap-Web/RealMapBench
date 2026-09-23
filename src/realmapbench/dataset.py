from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from realmapbench.scoring.direct import (
    CONTRACT_VERSION,
    SCORER_VERSION,
    direct_prompt_schema_hash,
    validate_contract,
)


TASK_TYPE_CODES = {
    "place_lookup": "PL",
    "nearby_search": "NS",
    "route_and_distance": "RD",
    "business_analysis": "BA",
    "spatial_analysis": "SA",
}
CASE_ID_RE = re.compile(r"^RMB-(PL|NS|RD|BA|SA)-\d{3}$")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: root must be an object")
    return payload


def canonical_hash(value: Any) -> str:
    payload = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest(
    dataset_path: Path,
    truth_path: Path,
    *,
    root: Path,
) -> dict[str, Any]:
    dataset = load_json(dataset_path)
    truth = load_json(truth_path)
    cases = _object_list(dataset.get("cases"), "dataset.cases")
    snapshots = _object_list(truth.get("snapshots"), "truth.snapshots")

    return {
        "schema_version": "realmapbench.release_manifest.v1",
        "dataset_id": dataset["dataset_id"],
        "dataset_revision": dataset["dataset_revision"],
        "truth_snapshot_id": truth["truth_snapshot_id"],
        "case_count": len(cases),
        "scorer_versions": {
            "direct": SCORER_VERSION,
            "rubric_contract": CONTRACT_VERSION,
        },
        "direct_prompt_schema_hash": direct_prompt_schema_hash(),
        "file_hashes": {
            dataset_path.relative_to(root).as_posix(): file_hash(dataset_path),
            truth_path.relative_to(root).as_posix(): file_hash(truth_path),
        },
        "case_hashes": {case["id"]: canonical_hash(case) for case in cases},
        "rubric_hashes": {
            case["id"]: canonical_hash(
                {
                    "rubric": case["rubric"],
                    "rubric_contract": case["rubric_contract"],
                }
            )
            for case in cases
        },
        "truth_value_hashes": {
            snapshot["case_id"]: canonical_hash(snapshot["value"])
            for snapshot in snapshots
        },
    }


def validate_release(
    dataset_path: Path,
    truth_path: Path,
    manifest_path: Path | None,
) -> dict[str, Any]:
    dataset_path = dataset_path.resolve()
    truth_path = truth_path.resolve()
    dataset = load_json(dataset_path)
    truth = load_json(truth_path)
    cases = _object_list(dataset.get("cases"), "dataset.cases")
    snapshots = _object_list(truth.get("snapshots"), "truth.snapshots")

    if dataset.get("dataset_id") != "realmapbench":
        raise ValueError("dataset_id must be realmapbench")
    if dataset.get("dataset_revision") != "realmapbench-v1-public-72-r2":
        raise ValueError("dataset_revision must be realmapbench-v1-public-72-r2")
    if len(cases) != 72 or dataset.get("case_count") != 72:
        raise ValueError("release must contain exactly 72 cases")
    if len(snapshots) != 72 or truth.get("ok_count") != 72:
        raise ValueError("truth sidecar must contain exactly 72 valid snapshots")

    case_by_id = _unique_by(cases, "id", "dataset cases")
    truth_by_id = _unique_by(snapshots, "case_id", "truth snapshots")
    if set(case_by_id) != set(truth_by_id):
        raise ValueError("dataset and truth case IDs must match")

    truth_snapshot_id = str(dataset.get("truth_snapshot_id") or "")
    if truth_snapshot_id != truth.get("truth_snapshot_id"):
        raise ValueError("dataset and truth snapshot IDs must match")
    if dataset.get("dataset_revision") != truth.get("dataset_revision"):
        raise ValueError("dataset and truth revisions must match")

    task_type_counts: Counter[str] = Counter()
    difficulty_counts: Counter[str] = Counter()
    for case_id, case in case_by_id.items():
        if CASE_ID_RE.fullmatch(case_id) is None:
            raise ValueError(f"invalid case ID: {case_id}")
        metadata = _mapping(case.get("metadata"), f"{case_id}.metadata")
        task_type = str(metadata.get("task_type") or "")
        expected_code = TASK_TYPE_CODES.get(task_type)
        if expected_code is None or not case_id.startswith(f"RMB-{expected_code}-"):
            raise ValueError(f"{case_id}: ID prefix does not match task_type")
        difficulty = str(metadata.get("difficulty") or "")
        if difficulty not in {"simple", "medium", "hard"}:
            raise ValueError(f"{case_id}: invalid difficulty")
        task_type_counts[task_type] += 1
        difficulty_counts[difficulty] += 1

        prompt = case.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"{case_id}: prompt must be non-empty")
        rubric = _mapping(case.get("rubric"), f"{case_id}.rubric")
        if not isinstance(rubric.get("goal"), str) or not rubric["goal"].strip():
            raise ValueError(f"{case_id}: rubric goal must be non-empty")
        if not isinstance(rubric.get("criteria"), list) or not rubric["criteria"]:
            raise ValueError(f"{case_id}: rubric criteria must be non-empty")
        validate_contract(_mapping(case.get("rubric_contract"), f"{case_id}.rubric_contract"))

        truth_ref = _mapping(case.get("truth"), f"{case_id}.truth")
        snapshot = truth_by_id[case_id]
        canonical_snapshot_id = f"{truth_snapshot_id}/{case_id}"
        if truth_ref.get("truth_snapshot_id") != truth_snapshot_id:
            raise ValueError(f"{case_id}: truth snapshot reference mismatch")
        if truth_ref.get("snapshot_id") != snapshot.get("snapshot_id"):
            raise ValueError(f"{case_id}: truth entry reference mismatch")
        if truth_ref.get("snapshot_id") != canonical_snapshot_id:
            raise ValueError(f"{case_id}: canonical snapshot ID mismatch")
        if truth_ref.get("mode") != "snapshot":
            raise ValueError(f"{case_id}: case truth mode must be snapshot")
        if truth_ref.get("release_mode") != "static" or snapshot.get("mode") != "static":
            raise ValueError(f"{case_id}: frozen truth mode must be static")
        if snapshot.get("status") != "ok" or "value" not in snapshot:
            raise ValueError(f"{case_id}: truth snapshot must have status=ok and value")
        if snapshot.get("value_hash") != canonical_hash(snapshot["value"]):
            raise ValueError(f"{case_id}: truth value hash mismatch")

    if dict(sorted(task_type_counts.items())) != dict(
        sorted(_mapping(dataset.get("task_type_counts"), "task_type_counts").items())
    ):
        raise ValueError("task_type_counts does not match cases")
    if dict(sorted(difficulty_counts.items())) != dict(
        sorted(_mapping(dataset.get("difficulty_counts"), "difficulty_counts").items())
    ):
        raise ValueError("difficulty_counts does not match cases")

    scoring = _mapping(dataset.get("scoring"), "dataset.scoring")
    if scoring.get("primary_metric") != "direct_task_pass":
        raise ValueError("primary metric must be direct_task_pass")
    if scoring.get("direct_scorer_version") != SCORER_VERSION:
        raise ValueError("direct scorer version mismatch")
    if scoring.get("direct_prompt_schema_hash") != direct_prompt_schema_hash():
        raise ValueError("direct prompt schema hash mismatch")

    if manifest_path is not None:
        manifest_path = manifest_path.resolve()
        manifest = load_json(manifest_path)
        expected = build_manifest(
            dataset_path,
            truth_path,
            root=manifest_path.parents[1],
        )
        if manifest != expected:
            raise ValueError("release manifest does not match dataset and truth")

    return {
        "dataset_revision": dataset["dataset_revision"],
        "truth_snapshot_id": truth_snapshot_id,
        "case_count": len(cases),
    }


def find_case(dataset: Mapping[str, Any], case_id: str) -> dict[str, Any]:
    for case in _object_list(dataset.get("cases"), "dataset.cases"):
        if case.get("id") == case_id:
            return case
    raise ValueError(f"unknown case ID: {case_id}")


def find_truth(truth: Mapping[str, Any], case_id: str) -> dict[str, Any]:
    for snapshot in _object_list(truth.get("snapshots"), "truth.snapshots"):
        if snapshot.get("case_id") == case_id:
            return snapshot
    raise ValueError(f"missing truth for case ID: {case_id}")


def _object_list(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{label} must be a list of objects")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _unique_by(
    rows: list[dict[str, Any]],
    key: str,
    label: str,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{label}: {key} must be a non-empty string")
        if value in result:
            raise ValueError(f"{label}: duplicate {key}: {value}")
        result[value] = row
    return result
