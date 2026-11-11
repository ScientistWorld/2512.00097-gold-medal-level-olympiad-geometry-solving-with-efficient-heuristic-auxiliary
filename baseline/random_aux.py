#!/usr/bin/env python3
"""Random auxiliary-construction baseline (paper Section 1 / Table 1-2).

Each of the K attempts adds N auxiliary points; every point is produced by a
random basic action (midpoint, reflection, foot, line/circle intersections,
triangle centres, perpendicular/parallel through a point) applied to randomly
chosen points of the current diagram.  Uses the same proposer interface and
budget as every other method.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from diagram import Geo, random_construction  # noqa: E402


def stable_seed(*parts) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16)


def propose_problem(row: dict, attempts: int, rounds: int, seed: int) -> list[list[str]]:
    coords = row.get("coords")
    if not coords:
        return []
    names = list(row["points"])
    geo = Geo(names, [coords[n] for n in names])
    rng = random.Random(stable_seed("random_aux", seed, row["problem_id"]))
    taken = set(names)
    aux_names = []
    i = 1
    while len(aux_names) < rounds:
        if f"aux{i}" not in taken:
            aux_names.append(f"aux{i}")
        i += 1
    out = []
    for _ in range(attempts):
        g = geo
        clauses = []
        for r in range(rounds):
            res = random_construction(g, rng)
            if res is None:
                break
            xy, body = res
            clauses.append(f"{aux_names[r]} = {body.format(x=aux_names[r])}")
            g = g.add(aux_names[r], xy)
        if clauses:
            out.append(clauses)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    with args.output.open("w", encoding="utf-8") as f:
        for row in rows:
            attempts = int(row.get("max_attempts", 16))
            rounds = min(args.rounds, int(row.get("max_aux_per_attempt", args.rounds)))
            try:
                proposals = propose_problem(row, attempts, rounds, args.seed)
            except Exception as exc:  # noqa: BLE001
                print(f"[random_aux] {row['problem_id']}: {type(exc).__name__}: {exc}", file=sys.stderr)
                proposals = []
            f.write(json.dumps({"problem_id": row["problem_id"], "attempts": proposals}) + "\n")


if __name__ == "__main__":
    main()
