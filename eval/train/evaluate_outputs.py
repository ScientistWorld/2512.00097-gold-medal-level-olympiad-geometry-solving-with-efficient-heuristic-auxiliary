#!/usr/bin/env python3
"""Train-slice scoring for solver output artifacts.

This evaluator is method-agnostic: it reads JSONL files produced under
outputs/ and scores a fixed visible subset of benchmark problem IDs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SLICE = "train"
REGISTERED_REFERENCE = Path("scoring/reference.json")

EXPERIMENTS = {
    "auxiliary_core": {
        "dataset": Path("data/benchmarks/auxiliary_core.jsonl"),
        "output_stem": "auxiliary_core",
        "required": True,
        "slice_ids": ["orthocenter_auxiliary"],
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
        "slice_ids": [
            "2014ARMOg9p6",
            "2012EGMOp1",
            "2010AsiaPacificMOp1",
            "2012CGMOp5",
            "2018CHNWesternMOp5",
            "2018SilkRoadp1",
        ],
        "metrics": [
            "solve_rate",
            "solved_count",
            "problem_count",
            "upper_band_solve_rate",
            "difficulty_weighted_solve_rate",
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


def registered_methods(path: Path) -> dict[str, set[str]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    experiments = data.get("experiments", {})
    return {
        exp_name: set(exp_data.get("results", {}))
        for exp_name, exp_data in experiments.items()
    }


def validate_rows(rows: list[dict], required_ids: list[str], output_path: Path) -> None:
    seen = [row.get("problem_id") for row in rows]
    missing = sorted(set(required_ids) - set(seen))
    duplicates = sorted({pid for pid in required_ids if seen.count(pid) > 1})
    if missing or duplicates:
        raise ValueError(
            f"{output_path}: invalid {SLICE} coverage; missing={missing}, "
            f"duplicates={duplicates}"
        )


def summarize(rows: list[dict], metric_names: list[str]) -> dict:
    solved_count = sum(1 for row in rows if row.get("solved"))
    upper_band_rows = [row for row in rows if float(row.get("difficulty", 0.0)) >= 1.4]
    difficulty_sum = sum(float(row.get("difficulty", 0.0)) for row in rows)
    summary = {
        "solved_count": solved_count,
        "problem_count": len(rows),
        "solve_rate": solved_count / len(rows) if rows else 0.0,
        "upper_band_solve_rate": (
            sum(1 for row in upper_band_rows if row.get("solved")) / len(upper_band_rows)
            if upper_band_rows
            else 0.0
        ),
        "difficulty_weighted_solve_rate": (
            sum(float(row.get("difficulty", 0.0)) for row in rows if row.get("solved"))
            / difficulty_sum
            if difficulty_sum
            else 0.0
        ),
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="scoring/scores_train.json", type=Path)
    args = parser.parse_args()

    allowed_methods = registered_methods(REGISTERED_REFERENCE)
    scores = {"slice": SLICE, "experiments": {}}
    for exp_name, config in EXPERIMENTS.items():
        dataset_path = config["dataset"]
        if not dataset_path.exists():
            if config.get("required"):
                raise FileNotFoundError(f"required benchmark is missing: {dataset_path}")
            continue

        expected_ids = benchmark_ids(dataset_path)
        selected_ids = config["slice_ids"]
        unknown_ids = sorted(set(selected_ids) - set(expected_ids))
        if unknown_ids:
            raise ValueError(f"{exp_name}: {SLICE} IDs missing from benchmark: {unknown_ids}")
        if not selected_ids:
            raise ValueError(f"{exp_name}: {SLICE} split selected no benchmark IDs")

        results = {}
        outputs = discover_outputs(config["output_stem"])
        if exp_name in allowed_methods:
            outputs = {
                method_name: output_path
                for method_name, output_path in outputs.items()
                if method_name in allowed_methods[exp_name]
            }
        if config.get("required") and not outputs:
            raise FileNotFoundError(
                f"{exp_name}: no solver outputs found for stem {config['output_stem']!r}"
            )

        for method_name, output_path in outputs.items():
            rows = read_jsonl(output_path)
            if not rows:
                continue
            validate_rows(rows, selected_ids, output_path)
            selected_id_set = set(selected_ids)
            slice_rows = [row for row in rows if row.get("problem_id") in selected_id_set]
            results[method_name] = summarize(slice_rows, config["metrics"])

        if results:
            scores["experiments"][exp_name] = {"results": results}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(scores, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
