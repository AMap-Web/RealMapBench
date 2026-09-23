from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def test_validate_cli_accepts_the_published_release():
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Validated 72 cases" in completed.stdout


@pytest.mark.parametrize("case_id", ["RMB-PL-001", "RMB-SA-011", "RMB-SA-014"])
def test_score_cli_prepares_request_and_aggregates_verdicts(tmp_path: Path, case_id: str):
    answer_path = tmp_path / "answer.txt"
    request_path = tmp_path / "request.json"
    verdict_path = tmp_path / "verdict.json"
    score_path = tmp_path / "score.json"
    evidence_path = tmp_path / "evidence.json"
    answer_path.write_text("北京市朝阳区朝阳北路101号。", encoding="utf-8")
    evidence_path.write_text(
        json.dumps(
            {
                "schema_version": "publication_safe_judge_evidence.v1",
                "evidence": [
                    {"kind": "declared", "label": "source", "value": "map"}
                ],
            }
        ),
        encoding="utf-8",
    )

    prepared = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "score.py"),
            "prepare",
            "--case-id",
            case_id,
            "--answer-file",
            str(answer_path),
            "--evidence-file",
            str(evidence_path),
            "--output",
            str(request_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert prepared.returncode == 0, prepared.stderr
    request = json.loads(request_path.read_text(encoding="utf-8"))
    criteria = request["contract"]["criteria"]
    assert "publication_safe_judge_evidence.v1" in request["prompt"]

    verdict_path.write_text(
        json.dumps(
            {
                "criteria": [
                    {
                        "id": criterion["id"],
                        "verdict": "pass",
                        "reason": "matched",
                        "evidence": ["final answer"],
                    }
                    for criterion in criteria
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    aggregated = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "score.py"),
            "aggregate",
            "--case-id",
            case_id,
            "--judge-response",
            str(verdict_path),
            "--output",
            str(score_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert aggregated.returncode == 0, aggregated.stderr
    score = json.loads(score_path.read_text(encoding="utf-8"))
    assert score["case_id"] == case_id
    assert score["task_pass"] is True
    assert score["score"] == 1.0
