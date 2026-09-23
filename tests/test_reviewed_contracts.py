from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data" / "realmapbench-v1.json"
TRUTH_PATH = ROOT / "data" / "realmapbench-v1.truth.json"


def _release() -> tuple[dict[str, dict], dict[str, dict]]:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    truth = json.loads(TRUTH_PATH.read_text(encoding="utf-8"))
    return (
        {case["id"]: case for case in dataset["cases"]},
        {snapshot["case_id"]: snapshot for snapshot in truth["snapshots"]},
    )


def _criteria(case: dict) -> dict[str, dict]:
    return {
        criterion["id"]: criterion
        for criterion in case["rubric_contract"]["criteria"]
    }


def _fields(case: dict) -> dict[str, dict]:
    return {
        field["path"]: field
        for field in case["rubric_contract"]["extraction"]["fields"]
    }


def test_reviewed_route_business_and_spatial_contracts_are_applied():
    cases, truth = _release()

    rd = _criteria(cases["RMB-RD-002"])["required.driving_distance"]
    assert rd["tolerance"] == {"mode": "absolute", "value": 1500}

    ba10 = cases["RMB-BA-010"]["rubric_contract"]
    assert ba10["expected"]["spatial_scope"] == "1公里"
    assert "1019" in _criteria(cases["RMB-BA-010"])["required.shopping_count"]["title"]

    ba14 = cases["RMB-BA-014"]["rubric_contract"]
    assert ba14["expected"] == {
        "counts": [434, 199, 2377, 3524, 161, 20, 1187, 1853],
        "differences": [273, 179, 1190, 1671],
    }
    assert _criteria(cases["RMB-BA-014"])["required.counts"]["operator"] == "ordered_numeric_tolerance"
    assert "2377" in truth["RMB-BA-014"]["value"]

    sa = cases["RMB-SA-005"]["rubric_contract"]
    assert sa["expected"]["poi_id_deduplicated_stop_count"] == 150
    assert _criteria(cases["RMB-SA-005"])["required.poi_id_deduplicated_stop_count"]["role"] == "required"


def test_public_grid_contracts_only_score_retained_counts():
    cases, _ = _release()
    assert cases["RMB-SA-011"]["rubric_contract"]["expected"] == {
        "bank_densest_count": 9,
        "bank_grid_count": 37,
        "coffee_shop_densest_count": 5,
        "coffee_shop_grid_count": 68,
    }
    assert cases["RMB-SA-014"]["rubric_contract"]["expected"] == {
        brand: {"max_store_count": 1}
        for brand in ("chagee", "heytea", "naixue")
    }
    for case_id, count in (("RMB-SA-011", 4), ("RMB-SA-014", 3)):
        case = cases[case_id]
        contract = case["rubric_contract"]
        assert "not evaluated" in contract["public_scoring_note"]
        assert case["metadata"]["public_scoring_note"] == contract["public_scoring_note"]
        assert len(contract["criteria"]) == count
        assert all(c["role"] == "required" for c in contract["criteria"])
        assert set(_fields(case)) == {
            c["actual_path"].removeprefix("actual.") for c in contract["criteria"]
        }


def test_reviewed_release_freezes_criterion_counts():
    cases, _ = _release()
    criteria = [
        criterion
        for case in cases.values()
        for criterion in case["rubric_contract"]["criteria"]
    ]

    assert len(criteria) == 329
    assert sum(criterion["role"] == "required" for criterion in criteria) == 263
    assert sum(criterion["role"] == "quality" for criterion in criteria) == 66


@pytest.mark.parametrize(
    "case_id,criterion_id,expected_count",
    [
        ("RMB-NS-012", "required.restaurant_count", 484),
        ("RMB-NS-012", "required.teahouse_count", 50),
        ("RMB-BA-001", "required.commercial_area_count", 10),
        ("RMB-BA-004", "required.commercial_area_count", 7),
        ("RMB-BA-006", "required.commercial_area_count", 3),
    ],
)
def test_judge_receives_consistent_count_titles(case_id, criterion_id, expected_count):
    from realmapbench.scoring.direct import build_direct_judge_request

    cases, truth = _release()
    case = cases[case_id]
    request = build_direct_judge_request(
        question=case["prompt"],
        truth_snapshot=truth[case_id],
        contract=case["rubric_contract"],
        final_answer=truth[case_id]["value"],
    )
    criterion = next(c for c in request["contract"]["criteria"] if c["id"] == criterion_id)
    assert [int(n) for n in re.findall(r"\d+", criterion["title"])] == [expected_count]
    field = criterion["expected_path"].removeprefix("expected.")
    assert request["contract"]["expected"][field] == expected_count


def test_restaurant_category_uses_the_reviewed_broad_scope():
    cases, _ = _release()
    case = cases["RMB-NS-012"]
    title = _criteria(case)["quality.restaurant_category"]["title"]
    assert "餐饮服务大类" in title
    assert "050000~050900" in title
    assert "050100" not in title
    assert "主体" in _criteria(case)["quality.dedup_method"]["title"]


def test_judge_reference_material_omits_operational_and_promotional_content():
    from realmapbench.scoring.direct import build_direct_judge_request

    cases, truth = _release()
    forbidden = re.compile(
        r"拦截|截流|垄断|占领|抢占|抢夺|收割|霸屏|头部水平|体量最大|绝对主力"
        r"|Excel.*?下载|bash|bc 除法|TC-011|rubric R2|aicloud_poi_brand_stats_polygon"
        r"|接下来|我先|我来|配额|超限|客流画像|客群画像|居住客流"
    )
    for case_id, case in cases.items():
        request = build_direct_judge_request(
            question=case["prompt"],
            truth_snapshot=truth[case_id],
            contract=case["rubric_contract"],
            final_answer="No answer supplied.",
        )
        serialized_truth = request["prompt"].split("Frozen truth snapshot:\n", 1)[1].split(
            "\n\nFull rubric contract:", 1
        )[0]
        reference = json.loads(serialized_truth)
        assert not forbidden.search(reference["value"]), case_id


def test_ring_reference_does_not_imply_increasing_density_from_total_counts():
    cases, truth = _release()
    contract = cases["RMB-BA-017"]["rubric_contract"]
    assert contract["expected"]["ring_1to2km"] == 1194
    assert contract["expected"]["count_1km"] == 982
    assert "供给密度明显从" not in truth["RMB-BA-017"]["value"]
    assert not {"category", "category_code", "poi_id"}.intersection(contract["expected"])
