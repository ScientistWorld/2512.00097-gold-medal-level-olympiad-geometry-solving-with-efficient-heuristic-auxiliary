#!/usr/bin/env python3
"""Audit proposer: goal-agnostic private DDAR lookahead (never part of the gym).

Measures how much private search with a public copy of the prover buys inside
the proposer's CPU budget.  Per problem: saturate DDAR on the premises, then on
premises + one HAGeo candidate at a time (best-supported candidates first) for
as long as the per-problem CPU share lasts.  Candidates that let DDAR derive
new facts about the original points are emitted first (most new facts
first); the reference HAGeo attempts fill the remaining slots.  The goal is
never read.
"""
from __future__ import annotations

import contextlib
import json
import random
import signal
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "method" / "hageo"))
sys.path.insert(0, str(ROOT / "method" / "alphageometry"))

from absl import logging as absl_logging  # noqa: E402

absl_logging.set_verbosity(absl_logging.ERROR)
import numpy as np  # noqa: E402
import ddar  # noqa: E402
import graph as gh  # noqa: E402
import numericals as nm  # noqa: E402
import problem as pr  # noqa: E402

import propose as hp  # noqa: E402
from diagram import Geo  # noqa: E402
from heuristics import full_pool  # noqa: E402

DEFS = pr.Definition.from_txt_file(str(ROOT / "method/alphageometry/defs.txt"), to_dict=True)
RULES = pr.Theorem.from_txt_file(str(ROOT / "method/alphageometry/rules.txt"), to_dict=True)
PRED = {"coll", "cyclic", "para", "perp", "cong", "midp", "eqangle", "eqratio"}


class _Stop(BaseException):
    pass


@contextlib.contextmanager
def cpu_limit(seconds: float):
    def _raise(*_):
        raise _Stop()

    prev = signal.signal(signal.SIGPROF, _raise)
    # Re-armed every 20 ms after the deadline: AlphaGeometry has bare `except:`
    # clauses that can swallow a single signal.
    signal.setitimer(signal.ITIMER_PROF, max(0.01, seconds), 0.02)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_PROF, 0)
        signal.signal(signal.SIGPROF, prev)


def build(statement: str, seed: int, tries: int = 30):
    p = pr.Problem.from_txt(statement, translate=False)
    random.seed(seed)
    np.random.seed(seed)
    for _ in range(tries):
        try:
            g = gh.Graph()
            added, plevel = [], 0
            for clause in p.clauses:
                adds, plevel = g.add_clause(clause, plevel, DEFS, verbose=False)
                added += adds
            g.plevel = plevel
        except (nm.InvalidLineIntersectError, nm.InvalidQuadSolveError, gh.DepCheckFailError,
                gh.PointTooCloseError, gh.PointTooFarError):
            continue
        g.url = p.url
        g.build_def = (p, DEFS)
        for add in added:
            g.add_algebra(add, level=0)
        return g, p
    return None, p


def saturate(statement: str, seed: int):
    g, p = build(statement, seed)
    if g is None:
        return None, []
    _, _, _, _, added = ddar.solve(g, RULES, p, max_level=1000, timeout=100000)
    return g, added


def new_fact_count(g_s, added, names: set) -> int:
    seen = set()
    count = 0
    for dep in added:
        if dep.name not in PRED:
            continue
        args = [getattr(a, "name", None) for a in dep.args]
        if any(a not in names for a in args):
            continue
        key = (dep.name, tuple(args))
        if key in seen:
            continue
        seen.add(key)
        try:
            if not g_s.check(dep.name, g_s.names2points(args)):
                count += 1
        except Exception:  # noqa: BLE001
            continue
    return count


def main() -> None:
    inp, outp = Path(sys.argv[1]), Path(sys.argv[2])
    rows = [json.loads(l) for l in inp.read_text().splitlines() if l.strip()]
    total_budget = max(120.0, 3.0 * len(rows))
    if rows:
        total_budget = max(120.0, float(rows[0].get("cpu_seconds_per_problem", 3.0)) * len(rows))
    usable = 0.6 * total_budget
    with outp.open("w") as f:
        for i, row in enumerate(rows):
            attempts_ref = hp.propose_problem(row, int(row["max_attempts"]), 2, 0)
            left_total = usable - time.process_time()
            share = left_total / max(1, len(rows) - i)
            productive = []
            if row.get("coords") and share > 0.2:
                names = list(row["points"])
                geo = Geo(names, [row["coords"][n] for n in names])
                pool = full_pool(geo, random.Random(0))
                pool.sort(key=lambda e: (-e["count"], e["reps"][0][0]))
                started = time.process_time()
                deadline = started + share
                try:
                    with cpu_limit(share):
                        g_s, _ = saturate(row["setup"], 0)
                        if g_s is not None:
                            for e in pool:
                                if time.process_time() > deadline:
                                    break
                                clause = "zz9 = " + e["reps"][0][2].format(x="zz9")
                                try:
                                    g, added = saturate(row["setup"] + "; " + clause, 0)
                                except _Stop:
                                    raise
                                except Exception:  # noqa: BLE001
                                    continue
                                if g is None:
                                    continue
                                k = new_fact_count(g_s, added, set(names))
                                if k > 0:
                                    productive.append((k, "aux1 = " + e["reps"][0][2].format(x="aux1")))
                except _Stop:
                    pass
                except Exception:  # noqa: BLE001
                    pass
                print(f"[lookahead] {row['problem_id']} share={share:.2f}s used={time.process_time() - started:.2f}s "
                      f"productive={len(productive)}", file=sys.stderr, flush=True)
            productive.sort(key=lambda kv: -kv[0])
            attempts = [[c] for _, c in productive]
            for a in attempts_ref:
                if len(attempts) >= int(row["max_attempts"]):
                    break
                if a not in attempts:
                    attempts.append(a)
            f.write(json.dumps({"problem_id": row["problem_id"], "attempts": attempts[: int(row["max_attempts"])]})
                    + "\n")
            f.flush()


if __name__ == "__main__":
    main()
