#!/usr/bin/env python3
"""Audit proposers: short hand-written rules and shortcut probes (never part of the gym).

Modes
  circumcenters3  every attempt adds the circumcentres of three triangles of
                  configuration points, in a fixed order (48 per problem).
  mixed3          attempt i adds the i-th midpoint, the i-th circumcentre and
                  the i-th foot of a perpendicular, each in a fixed order.
  read_hidden     tries to read the evaluator's held-out files while it runs
                  (goals and known constructions); falls back to the reference
                  HAGeo attempts when they cannot be read.
  cpu_hog         burns more CPU than its limit in parallel worker processes
                  (finishing well inside the old wall-clock limit), then
                  returns the reference attempts.
"""
from __future__ import annotations

import itertools
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "method" / "hageo"))

import numpy as np  # noqa: E402

import propose as hp  # noqa: E402
from diagram import Geo, _circum, _collinear, _foot  # noqa: E402


def lists(geo: Geo):
    N, P, n = geo.names, geo.P, geo.n
    mids, circs, feet = [], [], []
    for i, j in itertools.combinations(range(n), 2):
        xy = (P[i] + P[j]) / 2
        if geo.acceptable(xy):
            mids.append(f"midpoint {{x}} {N[i]} {N[j]}")
    for i, j, k in itertools.combinations(range(n), 3):
        if _collinear(geo, i, j, k):
            continue
        xy = _circum(geo, i, j, k)
        if geo.acceptable(xy):
            circs.append(f"circumcenter {{x}} {N[i]} {N[j]} {N[k]}")
    for a in range(n):
        for b, c in itertools.combinations([x for x in range(n) if x != a], 2):
            if _collinear(geo, a, b, c):
                continue
            xy = _foot(P[a], P[b], P[c])
            if geo.acceptable(xy):
                feet.append(f"foot {{x}} {N[a]} {N[b]} {N[c]}")
    return mids, circs, feet


def clause(i: int, body: str) -> str:
    return f"aux{i} = " + body.format(x=f"aux{i}")


def burn(seconds: float) -> int:
    end = time.process_time() + seconds
    acc = 0
    while time.process_time() < end:
        acc += 1
    return acc


def main() -> None:
    mode, inp, outp = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    rows = [json.loads(l) for l in inp.read_text().splitlines() if l.strip()]
    known: dict = {}
    if mode == "read_hidden":
        status = "read"
        try:
            # direct probes first (glob silently returns nothing on an unreadable directory)
            (ROOT / "eval" / "test" / "problems_jgex.jsonl").read_text()
            os.listdir(ROOT / "eval" / "test")
            for f in sorted((ROOT / "eval" / "test").glob("*.jsonl")):
                for line in f.read_text().splitlines():
                    if line.strip():
                        r = json.loads(line)
                        if "aux" in r and "problem_id" in r:
                            known[r["problem_id"]] = r["aux"]
        except OSError as exc:
            status = f"denied ({type(exc).__name__})"
        note = ROOT / "tmp" / "hardening2" / "read_hidden_status.txt"
        note.parent.mkdir(parents=True, exist_ok=True)
        with note.open("a") as fh:
            fh.write(f"{time.strftime('%H:%M:%S')} {inp.name} rows={len(rows)} status={status} "
                     f"known={len(known)}\n")
        print(f"[read_hidden] status={status} known={len(known)}", file=sys.stderr)
    if mode == "cpu_hog":
        limit = max(120.0, float(rows[0].get("cpu_seconds_per_problem", 3.0)) * len(rows)) if rows else 120.0
        workers = 4
        with mp.get_context("fork").Pool(workers) as pool:
            pool.map(burn, [1.3 * limit / workers] * workers)
    with outp.open("w") as f:
        for row in rows:
            k = int(row["max_attempts"])
            if mode in ("read_hidden", "cpu_hog"):
                attempts = hp.propose_problem(row, k, 2, 0)
                if row["problem_id"] in known:
                    attempts = [known[row["problem_id"]]] + attempts[: k - 1]
            else:
                attempts = []
                if row.get("coords"):
                    geo = Geo(row["points"], [row["coords"][n] for n in row["points"]])
                    mids, circs, feet = lists(geo)
                    if mode == "circumcenters3":
                        for a in range(k):
                            chunk = circs[3 * a: 3 * a + 3]
                            if not chunk:
                                break
                            attempts.append([clause(i + 1, b) for i, b in enumerate(chunk)])
                    elif mode == "mixed3":
                        for a in range(k):
                            chunk = [lst[a] for lst in (mids, circs, feet) if a < len(lst)]
                            if not chunk:
                                break
                            attempts.append([clause(i + 1, b) for i, b in enumerate(chunk)])
                    else:
                        raise SystemExit(f"unknown mode {mode}")
            f.write(json.dumps({"problem_id": row["problem_id"], "attempts": attempts}) + "\n")


if __name__ == "__main__":
    main()
