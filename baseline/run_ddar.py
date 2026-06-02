#!/usr/bin/env python3
"""DDAR-only baseline for geometry theorem proving."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "method" / "hageo"))

from run_hageo import load_defs_rules, read_jsonl, run_ddar  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", default=30, type=int)
    args = parser.parse_args()

    defs, rules = load_defs_rules()
    rows = read_jsonl(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for index, row in enumerate(rows, start=1):
            print(
                f"[ddar] {index}/{len(rows)} {row['problem_id']}",
                file=sys.stderr,
                flush=True,
            )
            solved, status, seconds = run_ddar(
                row["problem_id"], row["statement"], defs, rules, args.timeout
            )
            f.write(
                json.dumps(
                    {
                        "problem_id": row["problem_id"],
                        "source": row.get("source", ""),
                        "difficulty": row.get("difficulty"),
                        "solved": solved,
                        "status": "ddar_" + status,
                        "seconds": seconds,
                        "auxiliary_clauses": [],
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            f.flush()


if __name__ == "__main__":
    main()
