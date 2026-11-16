#!/usr/bin/env python3
"""HAGeo auxiliary-construction proposer (reference method).

For every problem the evaluator supplies the construction premises (no goal)
and a numerical drawing.  Following the paper (Section 4.5), each of the K
auxiliary-construction attempts consists of N rounds; in every round all
heuristic candidate points of the current (augmented) diagram are computed and
one is selected at random together with its defining construction.  The
evaluator then runs DDAR once on the premises plus the attempt's N
constructions.

Round-one selections walk a random permutation of the candidate set so that
the K attempts start from different points; later rounds sample uniformly
from the candidates of the augmented diagram.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402

from diagram import Geo, random_construction  # noqa: E402
from heuristics import full_pool  # noqa: E402


def stable_seed(*parts) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16)


def fresh_names(existing: list[str], k: int) -> list[str]:
    out, i = [], 1
    taken = set(existing)
    while len(out) < k:
        name = f"aux{i}"
        if name not in taken:
            out.append(name)
        i += 1
    return out


def clause(name: str, body: str) -> str:
    return f"{name} = {body.format(x=name)}"


def pick_rep(entry: dict, rng: random.Random) -> str:
    # Simplest defining construction of the selected point.
    return entry["reps"][0][2]


def propose_problem(row: dict, attempts: int, rounds: int, seed: int, order: str = "random",
                    require_favorable: bool = True, extended: bool = False) -> list[list[str]]:
    coords = row.get("coords")
    if not coords:
        return []
    names = list(row["points"])
    geo = Geo(names, [coords[n] for n in names])
    rng = random.Random(stable_seed(seed, row["problem_id"]))
    aux_names = fresh_names(names, rounds)

    pool1 = full_pool(geo, rng, require_favorable, extended=extended)
    if not pool1:
        return []
    if order == "ranked":
        perm = sorted(range(len(pool1)), key=lambda i: (-pool1[i]["count"], pool1[i]["reps"][0][0], i))
    else:
        perm = list(range(len(pool1)))
        rng.shuffle(perm)

    later_cache: dict = {}
    out = []
    for a in range(attempts):
        first = perm[a % len(perm)]
        entry = pool1[first]
        clauses = [clause(aux_names[0], pick_rep(entry, rng))]
        g = geo.add(aux_names[0], entry["xy"])
        chosen = [np.asarray(entry["xy"])]
        path = (first,)
        for r in range(1, rounds):
            if path not in later_cache:
                later_cache[path] = full_pool(g, rng, require_favorable, extended=extended)
            pool_r = [e for e in later_cache[path]
                      if all(np.linalg.norm(np.asarray(e["xy"]) - c) > 1e-6 * g.scale for c in chosen)]
            if not pool_r:
                res = random_construction(g, rng)
                if res is None:
                    break
                entry = {"xy": res[0], "reps": [(9, "random", res[1])], "count": 0}
                idx = -1
            elif order == "ranked":
                idx = min(range(len(pool_r)), key=lambda i: (-pool_r[i]["count"], pool_r[i]["reps"][0][0], i))
                entry = pool_r[idx]
            else:
                idx = rng.randrange(len(pool_r))
                entry = pool_r[idx]
            clauses.append(clause(aux_names[r], pick_rep(entry, rng)))
            g = g.add(aux_names[r], entry["xy"])
            chosen.append(np.asarray(entry["xy"]))
            path = path + (idx,)
        out.append(clauses)
    return out


def propose_hybrid(row: dict, attempts: int, rounds: int, seed: int, prefix: int,
                   extended: bool = False) -> list[list[str]]:
    """Variant: the `prefix` best-supported candidates first, then the paper's sampling."""
    ranked = propose_problem(row, min(prefix, attempts), rounds, seed, "ranked", extended=extended)
    sampled = propose_problem(row, max(0, attempts - len(ranked)), rounds, seed, "random", extended=extended)
    return (ranked + sampled)[:attempts]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--order", choices=["random", "ranked", "hybrid"], default="random")
    parser.add_argument("--ranked-prefix", type=int, default=6, help="hybrid order: ranked attempts first")
    parser.add_argument("--unfiltered", action="store_true",
                        help="ablation: ignore the favourable-incidence filter")
    parser.add_argument("--extended", action="store_true",
                        help="variant: also triangle centres, reflections in lines and perpendicular/parallel "
                             "lines cut by a line, under the same favourable-incidence filter")
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    with args.output.open("w", encoding="utf-8") as f:
        for row in rows:
            started = time.time()
            attempts = int(row.get("max_attempts", 16))
            rounds = min(args.rounds, int(row.get("max_aux_per_attempt", args.rounds)))
            try:
                if args.order == "hybrid":
                    proposals = propose_hybrid(row, attempts, rounds, args.seed, args.ranked_prefix,
                                               extended=args.extended)
                else:
                    proposals = propose_problem(row, attempts, rounds, args.seed, args.order, not args.unfiltered,
                                                extended=args.extended)
            except Exception as exc:  # noqa: BLE001 - one bad drawing must not sink the run
                print(f"[hageo] {row['problem_id']}: {type(exc).__name__}: {exc}", file=sys.stderr)
                proposals = []
            f.write(json.dumps({"problem_id": row["problem_id"], "attempts": proposals}) + "\n")
            f.flush()
            print(f"[hageo] {row['problem_id']} attempts={len(proposals)} {time.time() - started:.1f}s",
                  file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
