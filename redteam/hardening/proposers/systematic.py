#!/usr/bin/env python3
"""Audit variant: capped brute-force enumeration of elementary constructions.

Fixed order (as in the earlier red-team 'better_systematic' / 'brute_force'
runs): midpoints of all point pairs, feet of perpendiculars, intersections of
two lines, point reflections; one construction per attempt; the first K
drawable candidates.  No incidence filter, no goal information.
"""
import itertools, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "method" / "hageo"))
from diagram import Geo, _line_intersection  # noqa: E402

def candidates(geo):
    N, P = geo.names, geo.P
    for i, j in itertools.combinations(range(geo.n), 2):
        yield (P[i] + P[j]) / 2, f"midpoint {{x}} {N[i]} {N[j]}"
    for a in range(geo.n):
        for li in range(geo.L):
            if a in geo.Lpts[li]:
                continue
            b, c = geo.Lrep[li]
            nv = geo.Ln[li]
            yield P[a] - (P[a] @ nv - geo.Lc[li]) * nv, f"foot {{x}} {N[a]} {N[b]} {N[c]}"
    for l1, l2 in itertools.combinations(range(geo.L), 2):
        (a, b), (c, d) = geo.Lrep[l1], geo.Lrep[l2]
        xy = _line_intersection(P[a], P[b], P[c], P[d])
        if xy is not None:
            yield xy, f"on_line {{x}} {N[a]} {N[b]}, on_line {{x}} {N[c]} {N[d]}"
    for i, j in itertools.permutations(range(geo.n), 2):
        yield 2 * P[j] - P[i], f"mirror {{x}} {N[i]} {N[j]}"

rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
with open(sys.argv[2], "w") as f:
    for row in rows:
        out = []
        if row.get("coords"):
            geo = Geo(row["points"], [row["coords"][n] for n in row["points"]])
            for xy, body in candidates(geo):
                if geo.acceptable(xy):
                    out.append([f"aux1 = {body.format(x='aux1')}"])
                if len(out) >= int(row["max_attempts"]):
                    break
        f.write(json.dumps({"problem_id": row["problem_id"], "attempts": out}) + "\n")
