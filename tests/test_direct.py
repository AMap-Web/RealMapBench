from __future__ import annotations

import pytest


def _contract() -> dict[str, object]:
    return {
        "version": "rubric_contract.v1",
        "criteria": [
            {
                "id": "required.address",
                "title": "Correct address",
                "role": "required",
                "operator": "text_contains",
                "actual_path": "actual.address",
                "expected_path": "expected.address",
                "weight": 1,
                "evidence_refs": ["final_answer"],
            },
            {
                "id": "quality.explanation",
                "title": "Clear explanation",
                "role": "quality",
                "operator": "present",
                "actual_path": "actual.explanation",
                "expected_path": "expected.explanation",
                "weight": 1,
                "evidence_refs": ["final_answer"],
            },
        ],
        "expected": {"address": "101 Chaoyang North Road", "explanation": True},
        "extraction": {
            "fields": [
                {"path": "address", "type": "string", "description": "Address"},
                {
                    "path": "explanation",
                    "type": "string",
                    "description": "Explanation",
                },
            ]
        },
        "pass_policy": "all_required",
        "score_policy": "weighted_mean",
    }


def test_direct_request_contains_frozen_truth_contract_and_final_answer():
    from realmapbench.scoring.direct import SCORER_VERSION, build_direct_judge_request

    request = build_direct_judge_request(
        question="What is the address?",
        truth_snapshot={"status": "ok", "value": {"address": "101 Chaoyang North Road"}},
        contract=_contract(),
        final_answer="The address is 101 Chaoyang North Road.",
        publication_safe_evidence={
            "schema_version": "publication_safe_judge_evidence.v1",
            "evidence": [{"kind": "declared", "label": "source", "value": "map"}],
        },
    )

    assert request["scorer_version"] == SCORER_VERSION
    assert request["system"].startswith("You are a rubric-contract judge.")
    assert "Frozen truth snapshot" in request["prompt"]
    assert "101 Chaoyang North Road" in request["prompt"]
    assert "publication_safe_judge_evidence.v1" in request["prompt"]
    assert request["response_schema"]["verdicts"] == ["fail", "pass"]
    assert "40.81%" in request["system"]
    assert "582万" in request["system"]
    assert "percentage_point" in request["system"]


def test_direct_contract_accepts_reviewed_distance_and_percentage_point_units():
    from realmapbench.scoring.direct import validate_contract

    contract = _contract()
    contract["criteria"][0]["operator"] = "numeric_tolerance"
    contract["criteria"][0]["tolerance"] = {"mode": "absolute", "value": 0.2}
    contract["extraction"]["fields"][0] = {
        "path": "address",
        "type": "number",
        "canonical_unit": "percentage_point",
    }
    validate_contract(contract)

    contract["extraction"]["fields"][0]["canonical_unit"] = "km"
    validate_contract(contract)


def test_direct_scorer_requires_all_required_criteria_but_scores_quality_separately():
    from realmapbench.scoring.direct import SCORER_VERSION, score_direct_judge_response

    raw = """
    {
      "criteria": [
        {"id": "required.address", "verdict": "pass", "reason": "matched", "evidence": ["answer"]},
        {"id": "quality.explanation", "verdict": "fail", "reason": "missing", "evidence": []}
      ]
    }
    """

    score = score_direct_judge_response(contract=_contract(), raw_response=raw)

    assert score["scorer_version"] == SCORER_VERSION
    assert score["task_pass"] is True
    assert score["required_passed_count"] == 1
    assert score["quality_passed_count"] == 0
    assert score["score"] == 0.5


def test_direct_response_must_cover_every_contract_criterion_once():
    from realmapbench.scoring.direct import parse_direct_judge_response

    raw = '{"criteria":[{"id":"required.address","verdict":"pass","reason":"","evidence":[]}]}'

    with pytest.raises(ValueError, match="must match contract criteria"):
        parse_direct_judge_response(raw, _contract()["criteria"])
