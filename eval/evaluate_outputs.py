#!/usr/bin/env python3
"""Evaluate solver output artifacts without importing method code."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPERIMENTS = {
    "auxiliary_core": {
        "dataset": Path("data/benchmarks/auxiliary_core.jsonl"),
        "required": True,
        "outputs": {
            "ddar": Path("outputs/baseline_auxiliary_core.jsonl"),
            "hageo": Path("outputs/hageo_auxiliary_core.jsonl"),
        },
        "metrics": [
            "solve_rate",
            "solved_count",
            "problem_count",
            "mean_attempt_index",
            "mean_auxiliary_count",
            "attempt_budget",
            "rounds",
            "timeout_seconds",
            "neural_inference_used",
        ],
    },
    "hageo409_low_difficulty": {
        "dataset": Path("data/benchmarks/hageo409_small.jsonl"),
        "required": False,
        "outputs": {
            "random_aux_ddar": Path("outputs/random_aux_hageo409_small.jsonl"),
            "hageo": Path("outputs/hageo_hageo409_small.jsonl"),
        },
        "metrics": [
            "solve_rate",
            "solved_count",
            "problem_count",
            "attempt_budget",
            "rounds",
            "timeout_seconds",
            "neural_inference_used",
        ],
    }
}


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def benchmark_ids(path: Path) -> list[str]:
    return [row["problem_id"] for row in read_jsonl(path)]


def validate_rows(rows: list[dict], expected_ids: list[str], output_path: Path) -> None:
    seen = [row.get("problem_id") for row in rows]
    missing = sorted(set(expected_ids) - set(seen))
    extra = sorted(set(seen) - set(expected_ids))
    duplicates = sorted({pid for pid in seen if seen.count(pid) > 1})
    if missing or extra or duplicates:
        raise ValueError(
            f"{output_path}: invalid coverage; missing={missing}, extra={extra}, "
            f"duplicates={duplicates}"
        )


def summarize(rows: list[dict], metric_names: list[str]) -> dict:
    solved_count = sum(1 for row in rows if row.get("solved"))
    summary = {
        "solved_count": solved_count,
        "problem_count": len(rows),
        "solve_rate": solved_count / len(rows) if rows else 0.0,
        "mean_attempt_index": (
            sum(float(row.get("attempt_index", 0)) for row in rows) / len(rows) if rows else 0.0
        ),
        "mean_auxiliary_count": (
            sum(len(row.get("auxiliary_clauses", [])) for row in rows) / len(rows)
            if rows
            else 0.0
        ),
        "attempt_budget": max((int(row.get("attempt_budget", 0)) for row in rows), default=0),
        "rounds": max((int(row.get("rounds", 0)) for row in rows), default=0),
        "timeout_seconds": max((int(row.get("timeout_seconds", 0)) for row in rows), default=0),
        "neural_inference_used": max(
            (int(row.get("neural_inference_used", 0)) for row in rows), default=0
        ),
    }
    return {name: summary[name] for name in metric_names}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="scoring/scores.json", type=Path)
    args = parser.parse_args()

    scores = {"experiments": {}}
    for exp_name, config in EXPERIMENTS.items():
        dataset_path = config["dataset"]
        if not dataset_path.exists():
            if config.get("required"):
                raise FileNotFoundError(f"required benchmark is missing: {dataset_path}")
            continue
        expected_ids = benchmark_ids(dataset_path)
        results = {}
        for method_name, output_path in config["outputs"].items():
            if config.get("required") and not output_path.exists():
                raise FileNotFoundError(f"required solver output is missing: {output_path}")
            rows = read_jsonl(output_path)
            if not rows:
                continue
            validate_rows(rows, expected_ids, output_path)
            results[method_name] = summarize(rows, config["metrics"])
        if config.get("required") or results:
            missing_methods = sorted(set(config["outputs"]) - set(results))
            if missing_methods:
                raise FileNotFoundError(
                    f"{exp_name}: missing outputs for methods {missing_methods}"
                )
        if results:
            scores["experiments"][exp_name] = {"results": results}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(scores, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
