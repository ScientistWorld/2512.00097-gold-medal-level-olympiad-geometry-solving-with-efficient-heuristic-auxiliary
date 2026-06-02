#!/usr/bin/env python3
"""Evaluate solver output artifacts without importing method code."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPERIMENTS = {
    "auxiliary_core": {
        "dataset": Path("data/benchmarks/auxiliary_core.jsonl"),
        "outputs": {
            "ddar": Path("outputs/baseline_auxiliary_core.jsonl"),
            "hageo": Path("outputs/hageo_auxiliary_core.jsonl"),
        },
    }
}


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def summarize(rows: list[dict]) -> dict:
    if not rows:
        return {
            "solved_count": 0,
            "problem_count": 0,
            "solve_rate": 0.0,
            "mean_attempt_index": 0.0,
            "mean_auxiliary_count": 0.0,
        }
    solved_count = sum(1 for row in rows if row.get("solved"))
    return {
        "solved_count": solved_count,
        "problem_count": len(rows),
        "solve_rate": solved_count / len(rows),
        "mean_attempt_index": sum(float(row.get("attempt_index", 0)) for row in rows)
        / len(rows),
        "mean_auxiliary_count": sum(len(row.get("auxiliary_clauses", [])) for row in rows)
        / len(rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="scoring/scores.json", type=Path)
    args = parser.parse_args()

    scores = {"experiments": {}}
    for exp_name, config in EXPERIMENTS.items():
        if not config["dataset"].exists():
            continue
        results = {}
        for method_name, output_path in config["outputs"].items():
            rows = read_jsonl(output_path)
            if rows:
                results[method_name] = summarize(rows)
        if results:
            scores["experiments"][exp_name] = {"results": results}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(scores, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
