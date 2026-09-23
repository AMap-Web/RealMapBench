#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from realmapbench.dataset import find_case, find_truth, load_json  # noqa: E402
from realmapbench.scoring.direct import (  # noqa: E402
    build_direct_judge_request,
    score_direct_judge_response,
)


def _write(payload: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output is None:
        print(text, end="")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def _common_paths(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT / "data" / "realmapbench-v1.json",
    )
    parser.add_argument(
        "--truth",
        type=Path,
        default=ROOT / "data" / "realmapbench-v1.truth.json",
    )
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--output", type=Path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare and aggregate direct scores.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Build a vendor-neutral judge request.")
    _common_paths(prepare)
    prepare.add_argument("--answer-file", type=Path, required=True)
    prepare.add_argument(
        "--evidence-file",
        type=Path,
        help="Optional publication-safe evidence JSON; raw traces are not accepted.",
    )

    aggregate = subparsers.add_parser(
        "aggregate",
        help="Validate criterion verdicts and aggregate the direct score.",
    )
    _common_paths(aggregate)
    aggregate.add_argument("--judge-response", type=Path, required=True)

    args = parser.parse_args()
    dataset = load_json(args.dataset)
    case = find_case(dataset, args.case_id)

    if args.command == "prepare":
        truth = find_truth(load_json(args.truth), args.case_id)
        evidence = (
            load_json(args.evidence_file)
            if args.evidence_file is not None
            else None
        )
        payload = build_direct_judge_request(
            question=case["prompt"],
            truth_snapshot=truth,
            contract=case["rubric_contract"],
            final_answer=args.answer_file.read_text(encoding="utf-8"),
            publication_safe_evidence=evidence,
        )
        payload["case_id"] = args.case_id
    else:
        payload = score_direct_judge_response(
            contract=case["rubric_contract"],
            raw_response=args.judge_response.read_text(encoding="utf-8"),
        )
        payload["case_id"] = args.case_id

    _write(payload, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
