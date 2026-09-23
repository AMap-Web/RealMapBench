#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from realmapbench.dataset import validate_release  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the RealMapBench release.")
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
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data" / "realmapbench-v1.manifest.json",
    )
    args = parser.parse_args()

    summary = validate_release(args.dataset, args.truth, args.manifest)
    print(
        f"Validated {summary['case_count']} cases "
        f"for {summary['dataset_revision']}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
