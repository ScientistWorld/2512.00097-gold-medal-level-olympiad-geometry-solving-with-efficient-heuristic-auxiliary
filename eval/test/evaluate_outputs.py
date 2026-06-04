#!/usr/bin/env python3
"""Held-out test-slice scoring for solver output artifacts.

This evaluator is method-agnostic and mirrors eval/train/evaluate_outputs.py,
but scores the complementary held-out benchmark IDs. When train scores exist,
the test slice evaluates exactly the same method entries.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SLICE = "test"

EXPERIMENTS = {
    "auxiliary_core": {
        "dataset": Path("data/benchmarks/auxiliary_core.jsonl"),
        "output_stem": "auxiliary_core",
        "required": True,
        "split": "all",
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
        "output_stem": "hageo409_small",
        "required": False,
        "split": "odd",
        "metrics": [
            "solve_rate",
            "solved_count",
            "problem_count",
            "attempt_budget",
            "rounds",
            "timeout_seconds",
            "neural_inference_used",
        ],
    },
}

OUTPUT_ALIASES = {
    "baseline_auxiliary_core": "ddar",
    "hageo_auxiliary_core": "hageo",
    "baseline_hageo409_small": "ddar",
    "random_aux_hageo409_small": "random_aux_ddar",
    "hageo_hageo409_small": "hageo",
}


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def benchmark_ids(path: Path) -> list[str]:
    return [row["problem_id"] for row in read_jsonl(path)]


def slice_ids(ids: list[str], split: str) -> list[str]:
    if split == "all":
        return ids
    if split == "odd":
        return [pid for index, pid in enumerate(ids) if index % 2 == 1]
    raise ValueError(f"unsupported split selector: {split}")


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


def method_name_for_output(output_path: Path, output_stem: str) -> str | None:
    stem = output_path.stem
    if stem in OUTPUT_ALIASES:
        return OUTPUT_ALIASES[stem]
    suffix = f"_{output_stem}"
    if stem.endswith(suffix):
        return stem[: -len(suffix)]
    return None


def discover_outputs(output_stem: str) -> dict[str, Path]:
    outputs = {}
    for path in sorted(Path("outputs").glob(f"*_{output_stem}.jsonl")):
        method_name = method_name_for_output(path, output_stem)
        if method_name is None:
            continue
        if method_name in outputs:
            raise ValueError(
                f"multiple output files map to method {method_name!r}: "
                f"{outputs[method_name]} and {path}"
            )
        outputs[method_name] = path
    return outputs


def train_methods(path: Path) -> dict[str, set[str]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    experiments = data.get("experiments", {})
    return {
        exp_name: set(exp_data.get("results", {}))
        for exp_name, exp_data in experiments.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="scoring/scores_test.json", type=Path)
    parser.add_argument("--train-scores", default="scoring/scores_train.json", type=Path)
    args = parser.parse_args()

    required_methods = train_methods(args.train_scores)
    scores = {"slice": SLICE, "experiments": {}}
    for exp_name, config in EXPERIMENTS.items():
        dataset_path = config["dataset"]
        if not dataset_path.exists():
            if config.get("required"):
                raise FileNotFoundError(f"required benchmark is missing: {dataset_path}")
            continue

        expected_ids = benchmark_ids(dataset_path)
        selected_ids = set(slice_ids(expected_ids, config["split"]))
        if not selected_ids:
            raise ValueError(f"{exp_name}: {SLICE} split selected no benchmark IDs")

        outputs = discover_outputs(config["output_stem"])
        methods_to_score = required_methods.get(exp_name) or set(outputs)
        missing_outputs = sorted(methods_to_score - set(outputs))
        if missing_outputs:
            raise FileNotFoundError(
                f"{exp_name}: missing held-out outputs for train-scored methods "
                f"{missing_outputs}"
            )
        if config.get("required") and not methods_to_score:
            raise FileNotFoundError(
                f"{exp_name}: no solver outputs found for stem {config['output_stem']!r}"
            )

        results = {}
        for method_name in sorted(methods_to_score):
            output_path = outputs[method_name]
            rows = read_jsonl(output_path)
            if not rows:
                continue
            validate_rows(rows, expected_ids, output_path)
            slice_rows = [row for row in rows if row.get("problem_id") in selected_ids]
            results[method_name] = summarize(slice_rows, config["metrics"])

        if results:
            scores["experiments"][exp_name] = {"results": results}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(scores, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
