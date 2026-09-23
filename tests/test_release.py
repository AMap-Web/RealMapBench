from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "realmapbench-v1.json"
TRUTH_PATH = ROOT / "data" / "realmapbench-v1.truth.json"
MANIFEST_PATH = ROOT / "data" / "realmapbench-v1.manifest.json"

TASK_TYPE_CODES = {
    "place_lookup": "PL",
    "nearby_search": "NS",
    "route_and_distance": "RD",
    "business_analysis": "BA",
    "spatial_analysis": "SA",
}


def _load(path: Path) -> dict:
    assert path.is_file(), f"missing release artifact: {path.relative_to(ROOT)}"
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_hash(value: object) -> str:
    payload = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_release_has_72_semantic_cases_with_matching_truth_and_rubrics():
    from realmapbench.scoring.direct import validate_contract

    dataset = _load(DATASET_PATH)
    truth = _load(TRUTH_PATH)

    cases = dataset["cases"]
    snapshots = truth["snapshots"]
    assert len(cases) == 72
    assert len(snapshots) == 72

    case_ids = {case["id"] for case in cases}
    truth_ids = {snapshot["case_id"] for snapshot in snapshots}
    assert len(case_ids) == 72
    assert case_ids == truth_ids

    for case in cases:
        task_type = case["metadata"]["task_type"]
        code = TASK_TYPE_CODES[task_type]
        assert re.fullmatch(rf"RMB-{code}-\d{{3}}", case["id"])
        assert case["prompt"].strip()
        assert case["rubric"]["goal"].strip()
        assert case["rubric"]["criteria"]
        validate_contract(case["rubric_contract"])

    for snapshot in snapshots:
        assert snapshot["status"] == "ok"
        assert "value" in snapshot
        assert snapshot["value_hash"] == _canonical_hash(snapshot["value"])


def test_manifest_binds_dataset_truth_rubrics_and_scorer_versions():
    dataset = _load(DATASET_PATH)
    truth = _load(TRUTH_PATH)
    manifest = _load(MANIFEST_PATH)

    assert manifest["dataset_revision"] == "realmapbench-v1-public-72-r2"
    assert manifest["case_count"] == 72
    assert manifest["scorer_versions"] == {
        "direct": "rubric_contract_direct_v8",
        "rubric_contract": "rubric_contract.v1",
    }
    assert manifest["file_hashes"] == {
        "data/realmapbench-v1.json": _file_hash(DATASET_PATH),
        "data/realmapbench-v1.truth.json": _file_hash(TRUTH_PATH),
    }

    expected_case_hashes = {
        case["id"]: _canonical_hash(case) for case in dataset["cases"]
    }
    expected_rubric_hashes = {
        case["id"]: _canonical_hash(
            {
                "rubric": case["rubric"],
                "rubric_contract": case["rubric_contract"],
            }
        )
        for case in dataset["cases"]
    }
    expected_truth_hashes = {
        snapshot["case_id"]: _canonical_hash(snapshot["value"])
        for snapshot in truth["snapshots"]
    }
    assert manifest["case_hashes"] == expected_case_hashes
    assert manifest["rubric_hashes"] == expected_rubric_hashes
    assert manifest["truth_value_hashes"] == expected_truth_hashes


def test_manifest_builder_reproduces_the_published_manifest(tmp_path: Path):
    rebuilt_path = tmp_path / "manifest.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "build_manifest.py"),
            "--output",
            str(rebuilt_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert rebuilt_path.read_bytes() == MANIFEST_PATH.read_bytes()


def test_public_tree_contains_no_trace_or_experiment_artifacts():
    assert not (ROOT / "traces").exists()
    assert not (ROOT / "trace").exists()
    assert not (ROOT / "results").exists()

    forbidden = [
        re.compile(r"/(?:Users|home)/[^/\s]+/"),
        re.compile(r"\brun_[0-9a-f]{12,}\b"),
        re.compile(r"\btraj_[0-9a-f]{12,}\b"),
        re.compile(r"\btrace_[0-9a-f]{12,}\b"),
        re.compile(r"\bA" + r"MB-(?:PL|NS|RD|BA|SA|MF)-\d{3}\b"),
    ]
    ignored_parts = {
        ".git",
        ".idea",
        ".DS_Store",
        ".pytest_cache",
        ".venv",
        "__pycache__",
        "original_traces",
    }
    expected_files = {
        ".gitignore",
        "README.md",
        "data/realmapbench-v1.json",
        "data/realmapbench-v1.manifest.json",
        "data/realmapbench-v1.truth.json",
        "docs/data-scope.md",
        "docs/reproducibility.md",
        "pyproject.toml",
        "scripts/build_manifest.py",
        "scripts/score.py",
        "scripts/validate.py",
        "src/realmapbench/__init__.py",
        "src/realmapbench/dataset.py",
        "src/realmapbench/scoring/__init__.py",
        "src/realmapbench/scoring/direct.py",
        "tests/test_cli.py",
        "tests/test_direct.py",
        "tests/test_release.py",
        "tests/test_reviewed_contracts.py",
        "tests/test_validation.py",
        "uv.lock",
    }
    paths = [
        path
        for path in ROOT.rglob("*")
        if path.is_file() and not ignored_parts.intersection(path.parts)
    ]
    assert {path.relative_to(ROOT).as_posix() for path in paths} == expected_files
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            assert not pattern.search(text), f"{pattern.pattern} found in {path}"

    ignored = subprocess.run(
        ["git", "check-ignore", "original_traces/private-probe.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert ignored.returncode == 0
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    tracked_paths = set(filter(None, tracked.stdout.split("\0")))
    assert tracked_paths <= expected_files, tracked_paths - expected_files
    for tracked_path in tracked_paths:
        parts = Path(tracked_path).parts
        assert "__pycache__" not in parts, tracked_path
        assert not tracked_path.endswith((".pyc", ".pyo")), tracked_path

        payload = (ROOT / tracked_path).read_bytes()
        absolute_path_markers = (
            b"/" + b"Users" + b"/",
            b"/" + b"home" + b"/",
            b"/" + b"root" + b"/",
        )
        for marker in absolute_path_markers:
            assert marker not in payload, f"absolute path found in {tracked_path}"


def test_public_materials_do_not_include_internal_licensing_workflow():
    assert not (ROOT / "docs" / "licensing.md").exists()

    public_paths = (
        ROOT / "README.md",
        ROOT / "docs" / "data-scope.md",
        ROOT / "docs" / "reproducibility.md",
        DATASET_PATH,
    )
    forbidden_fragments = (
        "docs/licensing.md",
        "pending open-source approval",
        "pending_open_source_approval",
        "outstanding redistribution decisions",
        "not authorization to publish",
        "license status below",
        "publication and redistribution terms are pending",
        "rights-holder approval",
    )
    for path in public_paths:
        text = path.read_text(encoding="utf-8").casefold()
        for fragment in forbidden_fragments:
            assert fragment not in text, f"{fragment!r} found in {path}"


def test_dataset_and_truth_do_not_require_unpublished_trace_evidence():
    for path in (DATASET_PATH, TRUTH_PATH):
        text = path.read_text(encoding="utf-8").casefold()
        assert '"trajectory"' not in text
        assert "trace" not in text


def test_public_case_membership_excludes_withheld_questions_and_truth():
    dataset = _load(DATASET_PATH)
    truth = _load(TRUTH_PATH)
    manifest = _load(MANIFEST_PATH)
    counts = {"PL": 6, "NS": 16, "RD": 9, "BA": 22, "SA": 19}
    expected_ids = {
        f"RMB-{code}-{index:03d}"
        for code, count in counts.items()
        for index in range(1, count + 1)
    }
    assert {case["id"] for case in dataset["cases"]} == expected_ids
    assert {snapshot["case_id"] for snapshot in truth["snapshots"]} == expected_ids
    for key in ("case_hashes", "rubric_hashes", "truth_value_hashes"):
        assert set(manifest[key]) == expected_ids
    for path in (DATASET_PATH, TRUTH_PATH, MANIFEST_PATH):
        assert not re.search(r"RMB-MF-\d{3}", path.read_text(encoding="utf-8"))


def test_public_answers_and_contracts_contain_no_coordinate_values():
    pair = re.compile(r"(?<![\d.])\d{1,3}\.\d{3,}\s*[,，]\s*\d{1,3}\.\d{3,}(?![\d.])")
    coordinate_key = re.compile(r"(^|_)(lat|lon|lng|latitude|longitude)(_|$)|^densest_grid_centers$", re.I)

    def check(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                assert not coordinate_key.search(key), f"coordinate field at {path}.{key}"
                if key == "canonical_unit":
                    assert child != "degree", f"coordinate extraction at {path}"
                check(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                check(child, f"{path}[{index}]")
        elif isinstance(value, str):
            assert not pair.search(value), f"coordinate pair at {path}"

    for path in (DATASET_PATH, TRUTH_PATH):
        check(_load(path), path.name)


def test_public_truth_is_not_gitignored():
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", str(TRUTH_PATH)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, result.stdout + result.stderr
