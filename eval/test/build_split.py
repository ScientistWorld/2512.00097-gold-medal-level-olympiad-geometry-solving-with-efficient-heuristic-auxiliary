#!/usr/bin/env python3
"""Build the train/test problem sets from public HAGeo-409 (evaluator-owned).

``screen``: rename every point of each AlphaGeometry-format problem, draw it
with a fixed seed and run DDAR alone under a fixed timeout.  Results go to
``eval/test/screening.jsonl`` (resumable).

``split``: keep problems whose premises DDAR saturates *without* reaching the
goal (so an auxiliary construction is necessary), assign them to a visible
train set (``data/benchmarks/hageo409_train.jsonl``) and a hidden test set
(``eval/test/problems.jsonl``), stratified by human difficulty, and fix each
problem's per-attempt DDAR timeout from its saturation time.

Only ``screen`` needs the proof engine and pyarrow; ``split`` is pure Python.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARQUET = ROOT / "data" / "downloads" / "HAGeo-409" / "HAGeo-409.parquet"
JGEX = ROOT / "data" / "downloads" / "jgex_ag_231.txt"
SOURCES = {
    # source: (screening log, hidden test file, visible train file, id prefixes)
    "hageo409": (HERE / "screening.jsonl", HERE / "problems.jsonl",
                 ROOT / "data" / "benchmarks" / "hageo409_train.jsonl", ("test", "train")),
    "jgex": (HERE / "screening_jgex.jsonl", HERE / "problems_jgex.jsonl",
             ROOT / "data" / "benchmarks" / "jgex231_train.jsonl", ("jtest", "jtrain")),
}
SALT = "hageo-gym-v2"

NAME_POOL = [chr(c) for c in range(ord("a"), ord("z") + 1)] + [
    f"{chr(c)}{i}" for i in range(1, 4) for c in range(ord("a"), ord("z") + 1)
]


def stable_int(*parts) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


def rename_statement(statement: str, key: str) -> tuple[str, str, dict]:
    """Rename points to a per-problem random permutation of short names."""
    setup, goal = statement.split(" ? ", 1)
    clauses = [c.strip() for c in setup.split(";") if c.strip()]
    order: list[str] = []
    for clause in clauses:
        lhs = clause.split(" = ", 1)[0]
        for name in lhs.split():
            name = name.split("@", 1)[0]
            if name not in order:
                order.append(name)
    pool = NAME_POOL[:]
    random.Random(stable_int(SALT, "names", key)).shuffle(pool)
    mapping = dict(zip(order, pool))
    if len(mapping) != len(order):
        raise ValueError("too many points to rename")

    def sub(token: str) -> str:
        return mapping.get(token, token)

    out_clauses = []
    for clause in clauses:
        lhs, rhs = clause.split(" = ", 1)
        new_lhs = " ".join(sub(n.split("@", 1)[0]) for n in lhs.split())
        parts = []
        for part in rhs.split(","):
            toks = part.split()
            parts.append(" ".join([toks[0]] + [sub(t) for t in toks[1:]]))
        out_clauses.append(f"{new_lhs} = " + ", ".join(parts))
    gtoks = goal.split()
    new_goal = " ".join([gtoks[0]] + [sub(t) for t in gtoks[1:]])
    return "; ".join(out_clauses), new_goal, mapping


def load_hageo409() -> list[dict]:
    import pyarrow.parquet as pq

    table = pq.read_table(PARQUET).to_pydict()
    rows = []
    for i in range(len(table["Problem_ID"])):
        statement = table["AlphaGeometry"][i]
        if not statement or " ? " not in statement:
            continue
        rows.append(
            {
                "source_id": table["Problem_ID"][i],
                "difficulty": float(table["Difficulty_Score"][i]),
                "statement": statement,
                "natural_language": table["Natural_Language"][i],
            }
        )
    return rows


def load_jgex() -> list[dict]:
    lines = [l.strip() for l in JGEX.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = []
    for url, statement in zip(lines[0::2], lines[1::2]):
        if " ? " not in statement:
            continue
        rows.append({"source_id": url, "difficulty": None, "statement": statement, "natural_language": ""})
    return rows


def cmd_screen(args) -> None:
    sys.path.insert(0, str(HERE))
    import engine

    SCREENING = SOURCES[args.source][0]

    done = {}
    if SCREENING.exists():
        for line in SCREENING.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                done[row["source_id"]] = row
    rows = load_hageo409() if args.source == "hageo409" else load_jgex()
    prepared = []
    for row in rows:
        try:
            setup, goal, _ = rename_statement(row["statement"], row["source_id"])
        except Exception as exc:  # noqa: BLE001
            prepared.append((0, row, None, None, f"rename_error:{exc}"))
            continue
        prepared.append((len(engine_names(setup)), row, setup, goal, None))
    # Smallest configurations first: they are the ones DDAR can saturate.
    prepared.sort(key=lambda t: (t[0], t[1]["difficulty"] or 0.0, t[1]["source_id"]))
    started = time.time()
    with SCREENING.open("a", encoding="utf-8") as f:
        for n_points, row, setup, goal, error in prepared:
            if row["source_id"] in done:
                continue
            if time.time() - started > args.budget_seconds:
                print("[screen] time budget reached", file=sys.stderr, flush=True)
                break
            if error is not None:
                f.write(json.dumps(dict(row, status=error, seconds=0.0)) + "\n")
                continue
            rec = dict(row, setup=setup, goal=goal, n_points=n_points,
                       seed=stable_int(SALT, "seed", row["source_id"]))
            if n_points > args.max_points:
                rec.update(status="skipped_size", seconds=0.0)
            else:
                status, seconds = engine.verify(setup, goal, [], rec["seed"], args.timeout)
                rec.update(status=status, seconds=round(seconds, 3), screen_timeout=args.timeout)
            f.write(json.dumps(rec) + "\n")
            f.flush()
            print(f"[screen] {row['source_id']} d={row['difficulty']} n={n_points} "
                  f"{rec['status']} {rec['seconds']}", file=sys.stderr, flush=True)


def engine_names(setup: str) -> list[str]:
    names = []
    for clause in setup.split("; "):
        for n in clause.split(" = ", 1)[0].split():
            if n not in names:
                names.append(n)
    return names


def attempt_timeout(t_sat: float, args) -> int:
    return int(min(args.timeout_max, max(args.timeout_min, math.ceil(args.timeout_mult * t_sat + args.timeout_add))))


def cmd_split(args) -> None:
    SCREENING, TEST_OUT, TRAIN_OUT, (test_prefix, train_prefix) = SOURCES[args.source]
    rows = [json.loads(l) for l in SCREENING.read_text(encoding="utf-8").splitlines() if l.strip()]
    pool = [r for r in rows if r.get("status") == "saturated" and r["seconds"] <= args.sat_max]
    pool.sort(key=lambda r: (r["difficulty"] or 0.0, r["source_id"]))
    rng = random.Random(stable_int(SALT, "split"))
    test, train = [], []
    # Stratify by difficulty: within each consecutive block, send a fixed
    # share to the hidden test set.
    block = args.block
    for i in range(0, len(pool), block):
        chunk = pool[i:i + block]
        rng.shuffle(chunk)
        n_test = round(len(chunk) * args.test_fraction)
        test += chunk[:n_test]
        train += chunk[n_test:]

    def finalize(items, prefix, budget):
        items = sorted(items, key=lambda r: (r["difficulty"] or 0.0, r["source_id"]))
        rng2 = random.Random(stable_int(SALT, prefix))
        rng2.shuffle(items)
        out, cost = [], 0.0
        for r in items:
            t = attempt_timeout(r["seconds"], args)
            expected = args.max_attempts * min(t, args.cost_mult * r["seconds"] + 0.5)
            if cost + expected > budget:
                continue
            cost += expected
            out.append((r, t))
        out.sort(key=lambda rt: (rt[0]["difficulty"] or 0.0, rt[0]["source_id"]))
        rows_out = []
        for idx, (r, t) in enumerate(out, start=1):
            rows_out.append({
                "problem_id": f"{prefix}_{idx:03d}",
                "source_id": r["source_id"],
                "difficulty": r["difficulty"],
                "setup": r["setup"],
                "goal": r["goal"],
                "seed": r["seed"],
                "timeout": t,
                "ddar_alone_seconds": r["seconds"],
                "natural_language": r.get("natural_language", ""),
            })
        return rows_out, cost

    test_rows, test_cost = finalize(test, test_prefix, args.test_budget)
    train_rows, train_cost = finalize(train, train_prefix, args.train_budget)
    for path, rows_out in ((TEST_OUT, test_rows), (TRAIN_OUT, train_rows)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for r in rows_out:
                f.write(json.dumps(r, sort_keys=True) + "\n")

    def median(xs):
        xs = sorted(xs)
        return xs[len(xs) // 2] if xs else 0.0

    print(json.dumps({
        "pool": len(pool),
        "test": len(test_rows), "test_cost_upper": round(test_cost),
        "train": len(train_rows), "train_cost_upper": round(train_cost),
        "test_median_difficulty": median([r["difficulty"] or 0.0 for r in test_rows]),
        "train_median_difficulty": median([r["difficulty"] or 0.0 for r in train_rows]),
    }, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("screen")
    s.add_argument("--source", choices=sorted(SOURCES), default="hageo409")
    s.add_argument("--timeout", type=float, default=6.0)
    s.add_argument("--max-points", type=int, default=13)
    s.add_argument("--budget-seconds", type=float, default=2700)
    s.set_defaults(func=cmd_screen)
    p = sub.add_parser("split")
    p.add_argument("--source", choices=sorted(SOURCES), default="hageo409")
    p.add_argument("--sat-max", type=float, default=4.0)
    p.add_argument("--block", type=int, default=5)
    p.add_argument("--test-fraction", type=float, default=0.6)
    p.add_argument("--max-attempts", type=int, default=16)
    p.add_argument("--timeout-mult", type=float, default=5.0)
    p.add_argument("--timeout-add", type=float, default=4.0)
    p.add_argument("--timeout-min", type=float, default=6.0)
    p.add_argument("--timeout-max", type=float, default=20.0)
    p.add_argument("--cost-mult", type=float, default=3.0)
    p.add_argument("--test-budget", type=float, default=3000)
    p.add_argument("--train-budget", type=float, default=2000)
    p.set_defaults(func=cmd_split)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
