#!/usr/bin/env python3
"""Random auxiliary-construction baseline from the HAGeo paper."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "method" / "hageo"))

from run_hageo import (  # noqa: E402
    insert_aux,
    load_defs_rules,
    random_construction_candidates,
    random_construction_candidates_from_graph,
    read_jsonl,
    run_ddar,
    run_ddar_state,
)


def solve_with_random_aux(
    row: dict,
    defs: dict,
    rules: dict,
    attempts: int,
    rounds: int,
    timeout: int,
    seed: int,
) -> dict:
    problem_id = row["problem_id"]
    statement = row["statement"]
    solved, status, seconds, graph = run_ddar_state(problem_id, statement, defs, rules, timeout)
    result = {
        "problem_id": problem_id,
        "source": row.get("source", ""),
        "difficulty": row.get("difficulty"),
        "solved": solved,
        "attempt_index": 0,
        "attempt_budget": attempts,
        "rounds": rounds,
        "timeout_seconds": timeout,
        "neural_inference_used": 0,
        "auxiliary_clauses": [],
        "status": "ddar_" + status,
        "seconds": seconds,
    }
    if solved:
        return result

    if graph is not None:
        candidates = random_construction_candidates_from_graph(
            graph, max_candidates=max(128, attempts * rounds * 4)
        )
    else:
        candidates = random_construction_candidates(
            statement, defs, max_candidates=max(128, attempts * rounds * 4)
        )
    if not candidates:
        result["status"] = "random_aux_no_candidates"
        return result

    rng = random.Random(seed)
    total_seconds = seconds
    for idx in range(1, attempts + 1):
        chosen = []
        candidate_statement = statement
        for _round_index in range(rounds):
            aux = rng.choice(candidates)
            chosen.append(aux)
            candidate_statement = insert_aux(candidate_statement, [aux])
            solved, status, elapsed = run_ddar(problem_id, candidate_statement, defs, rules, timeout)
            total_seconds += elapsed
            if solved:
                result.update(
                    {
                        "solved": True,
                        "attempt_index": idx,
                        "auxiliary_clauses": chosen,
                        "status": "random_aux_" + status,
                        "seconds": total_seconds,
                    }
                )
                return result

    result["seconds"] = total_seconds
    result["status"] = "random_aux_failed"
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--attempts", default=32, type=int)
    parser.add_argument("--rounds", default=1, type=int)
    parser.add_argument("--timeout", default=30, type=int)
    parser.add_argument("--seed", default=0, type=int)
    args = parser.parse_args()

    defs, rules = load_defs_rules()
    rows = read_jsonl(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    with args.output.open("w", encoding="utf-8") as f:
        for index, row in enumerate(rows, start=1):
            print(
                f"[random_aux] {index}/{len(rows)} {row['problem_id']}",
                file=sys.stderr,
                flush=True,
            )
            out = solve_with_random_aux(
                row, defs, rules, args.attempts, args.rounds, args.timeout, args.seed + index
            )
            f.write(json.dumps(out, sort_keys=True) + "\n")
            f.flush()
    print(f"[random_aux] finished in {time.time() - started:.2f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
