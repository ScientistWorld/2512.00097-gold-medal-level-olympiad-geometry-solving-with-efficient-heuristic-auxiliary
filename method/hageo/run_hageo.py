#!/usr/bin/env python3
"""HAGeo-style heuristic auxiliary construction search over DDAR.

The released HAGeo repository does not yet contain solver source code. This
reproduction preserves the paper's computation pattern by using the public
AlphaGeometry DDAR engine as the symbolic DD+AR prover and adding CPU-only
heuristic auxiliary construction attempts before rerunning DDAR.
"""

from __future__ import annotations

import argparse
import contextlib
import itertools
import json
import random
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AG = ROOT / "method" / "alphageometry"
sys.path.insert(0, str(AG))

import ddar  # type: ignore  # noqa: E402
import graph as gh  # type: ignore  # noqa: E402
import problem as pr  # type: ignore  # noqa: E402


class DDARTimeout(RuntimeError):
    """Raised when a single DDAR call exceeds the hard wall-clock budget."""


@contextlib.contextmanager
def hard_timeout(seconds: int):
    if seconds <= 0:
        yield
        return

    def _raise_timeout(_signum, _frame):
        raise DDARTimeout(f"DDAR call exceeded {seconds} seconds")

    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, 0)
    signal.signal(signal.SIGALRM, _raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_timer[0] > 0:
            signal.setitimer(signal.ITIMER_REAL, previous_timer[0], previous_timer[1])


def load_defs_rules() -> tuple[dict, dict]:
    defs = pr.Definition.from_txt_file(str(AG / "defs.txt"), to_dict=True)
    rules = pr.Theorem.from_txt_file(str(AG / "rules.txt"), to_dict=True)
    return defs, rules


def parse_problem(problem_id: str, statement: str) -> pr.Problem:
    return pr.Problem.from_txt(f"{problem_id}\n{statement}", translate=False)


def run_ddar(
    problem_id: str,
    statement: str,
    defs: dict,
    rules: dict,
    timeout: int,
) -> tuple[bool, str, float]:
    start = time.time()
    try:
        with hard_timeout(timeout):
            p = parse_problem(problem_id, statement)
            g, _ = gh.Graph.build_problem(p, defs, verbose=False)
            ddar.solve(g, rules, p, max_level=1000, timeout=timeout)
            goal_args = g.names2nodes(p.goal.args)
            solved = bool(g.check(p.goal.name, goal_args))
        return solved, "solved" if solved else "failed", time.time() - start
    except DDARTimeout:
        return False, "timeout", time.time() - start
    except Exception as exc:  # DDAR can reject numerically degenerate drawings.
        return False, f"error:{type(exc).__name__}:{exc}", time.time() - start


def insert_aux(statement: str, aux_clauses: list[str]) -> str:
    setup, goal = statement.split(" ? ", 1)
    return setup + "; " + "; ".join(aux_clauses) + " ? " + goal


def point_names(statement: str) -> list[str]:
    setup = statement.split(" ? ", 1)[0]
    names: list[str] = []
    for clause in setup.split("; "):
        lhs = clause.split(" = ", 1)[0].strip()
        for name in lhs.split():
            if name and name not in names:
                names.append(name)
        rhs = clause.split(" = ", 1)[1] if " = " in clause else ""
        for token in rhs.replace(",", " ").split():
            if token.isidentifier() and token not in names:
                names.append(token)
    return names


def pair_lines(points: list[str]) -> list[tuple[str, str]]:
    return [(a, b) for a, b in itertools.combinations(points, 2)]


def candidate_auxiliaries(statement: str, max_candidates: int) -> list[str]:
    """Generate HAGeo heuristic construction categories.

    Categories implemented here are the paper's basic auxiliary operations:
    intersections of lines, midpoints, point reflections, and perpendicular
    feet. Candidates are generated from the current problem's named points.
    """
    pts = point_names(statement)
    candidates: list[str] = []
    counter = 0

    def add(template: str) -> None:
        nonlocal counter
        if len(candidates) >= max_candidates:
            return
        name = f"x{counter}"
        counter += 1
        candidates.append(template.format(x=name))

    lines = pair_lines(pts)
    # Prioritize intersections using at least one constructed point, matching
    # common auxiliary geometry moves such as intersecting two altitudes.
    for (a, b), (c, d) in itertools.combinations(lines, 2):
        if len({a, b, c, d}) < 4:
            continue
        add(f"{{x}} = on_line {{x}} {a} {b}, on_line {{x}} {c} {d}")
    for a, b in lines:
        add(f"{{x}} = midpoint {{x}} {a} {b}")
    for a, b in itertools.permutations(pts, 2):
        add(f"{{x}} = mirror {{x}} {a} {b}")
    for p in pts:
        for a, b in lines:
            if p in (a, b):
                continue
            add(f"{{x}} = foot {{x}} {p} {a} {b}")
    return candidates


def solve_with_hageo(
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
    solved, status, seconds = run_ddar(problem_id, statement, defs, rules, timeout)
    result = {
        "problem_id": problem_id,
        "source": row.get("source", ""),
        "difficulty": row.get("difficulty"),
        "solved": solved,
        "attempt_index": 0,
        "auxiliary_clauses": [],
        "status": "ddar_" + status,
        "seconds": seconds,
    }
    if solved:
        return result

    candidates = candidate_auxiliaries(statement, max_candidates=max(128, attempts * rounds * 2))
    rng = random.Random(seed)
    ordered = candidates[:]
    rng.shuffle(ordered)
    # Keep the deterministic order as a prefix so canonical intersections are
    # tried early; use shuffled candidates afterward for HAGeo's stochastic K.
    ordered = candidates[: min(len(candidates), attempts)] + ordered

    total_seconds = seconds
    for idx in range(1, attempts + 1):
        start = (idx - 1) * rounds
        aux = ordered[start : start + rounds]
        if not aux:
            break
        candidate_statement = insert_aux(statement, aux)
        solved, status, elapsed = run_ddar(problem_id, candidate_statement, defs, rules, timeout)
        total_seconds += elapsed
        if solved:
            result.update(
                {
                    "solved": True,
                    "attempt_index": idx,
                    "auxiliary_clauses": aux,
                    "status": "hageo_" + status,
                    "seconds": total_seconds,
                }
            )
            return result
    result["seconds"] = total_seconds
    result["status"] = "hageo_failed"
    return result


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


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
    with args.output.open("w", encoding="utf-8") as f:
        for index, row in enumerate(rows, start=1):
            print(
                f"[hageo] {index}/{len(rows)} {row['problem_id']}",
                file=sys.stderr,
                flush=True,
            )
            out = solve_with_hageo(row, defs, rules, args.attempts, args.rounds, args.timeout, args.seed)
            f.write(json.dumps(out, sort_keys=True) + "\n")
            f.flush()


if __name__ == "__main__":
    main()
