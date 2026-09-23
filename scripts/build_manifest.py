#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from realmapbench.dataset import build_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the RealMapBench release manifest.")
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
        "--output",
        type=Path,
        default=ROOT / "data" / "realmapbench-v1.manifest.json",
    )
    args = parser.parse_args()

    manifest = build_manifest(
        args.dataset.resolve(),
        args.truth.resolve(),
        root=ROOT,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
