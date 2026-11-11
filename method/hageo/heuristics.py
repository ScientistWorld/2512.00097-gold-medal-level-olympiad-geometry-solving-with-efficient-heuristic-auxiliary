"""HAGeo heuristic auxiliary points (paper Section 4.5, Figure 4).

A candidate is a *basic* construction -- intersection of two lines, of a line
and a circle, of two circles, a midpoint, a point reflection, or a foot of a
perpendicular -- that numerical computation shows to lie *non-trivially* on a
further line or circle of the configuration.  The favourable incidence is the
reason for choosing the point; it is never added as a premise: every emitted
clause only states the defining construction.

Lines pass through two configuration points; circles pass through three
configuration points or are centred at a configuration point and pass through
another.  Line/circle and circle/circle intersections are taken through a
configuration point lying on both objects (the second intersection), which the
engine's construction language determines uniquely.

The paper's identical-point heuristic (re-introducing an existing point as a
new multi-object intersection) is omitted: the DDAR engine used here rejects
coincident points.
"""

from __future__ import annotations

import numpy as np

from diagram import Geo, random_construction

PRIORITY = {"midpoint": 0, "mirror": 1, "foot": 2, "line_line": 3, "line_circle": 4, "circle_circle": 5}
MAX_ROWS = 60000
CHUNK = 8192


def _blocks(geo: Geo, rng):
    """Yield candidate blocks: (category, X, bodies, exL, exC1, exC2, foot_pt)."""
    n, P, N = geo.n, geo.P, geo.names
    if n < 3 or geo.L == 0:
        return

    # 3. midpoints and 4. point reflections
    I, J = np.triu_indices(n, 1)
    keep = [k for k in range(len(I)) if (int(I[k]), int(J[k])) in geo.pair_line]
    I, J = I[keep], J[keep]
    exL = np.array([geo.line_of(int(i), int(j)) for i, j in zip(I, J)], dtype=int)
    yield ("midpoint", (P[I] + P[J]) / 2, lambda k: f"midpoint {{x}} {N[I[k]]} {N[J[k]]}",
           exL, None, None, None)
    I2 = np.concatenate([I, J])
    J2 = np.concatenate([J, I])
    yield ("mirror", 2 * P[J2] - P[I2], lambda k: f"mirror {{x}} {N[I2[k]]} {N[J2[k]]}",
           np.concatenate([exL, exL]), None, None, None)

    # 5. feet of perpendiculars (incidence with another line only)
    rows = [(a, li) for li in range(geo.L) for a in range(n) if a not in geo.Lpts[li]]
    if rows:
        A = np.array([r[0] for r in rows])
        Li = np.array([r[1] for r in rows])
        nv = geo.Ln[Li]
        dist = (P[A] * nv).sum(1) - geo.Lc[Li]
        X = P[A] - dist[:, None] * nv
        def foot_body(k):
            b, c = geo.Lrep[int(Li[k])]
            return f"foot {{x}} {N[A[k]]} {N[b]} {N[c]}"

        yield ("foot", X, foot_body, Li, None, None, A)

    # 1. two lines (a third line or a circle through the intersection)
    LI, LJ = np.triu_indices(geo.L, 1)
    if len(LI):
        n1, n2 = geo.Ln[LI], geo.Ln[LJ]
        det = n1[:, 0] * n2[:, 1] - n1[:, 1] * n2[:, 0]
        ok = np.abs(det) > 1e-8
        LI, LJ, n1, n2, det = LI[ok], LJ[ok], n1[ok], n2[ok], det[ok]
        c1, c2 = geo.Lc[LI], geo.Lc[LJ]
        X = np.stack([(n2[:, 1] * c1 - n1[:, 1] * c2) / det, (n1[:, 0] * c2 - n2[:, 0] * c1) / det], axis=1)
        yield ("line_line", X, lambda k: f"{geo.line_text(int(LI[k]))}, {geo.line_text(int(LJ[k]))}",
               LI, LJ, None, None)

    # 2a. a line and a circle through a common configuration point
    trip = [(ci, p, li) for ci in range(geo.C) for p in geo.Cpts[ci] for li in geo.point_lines[p]]
    if trip:
        Ci = np.array([t[0] for t in trip])
        Pp = np.array([t[1] for t in trip])
        Li = np.array([t[2] for t in trip])
        u = np.stack([geo.Ln[Li][:, 1], -geo.Ln[Li][:, 0]], axis=1)
        t = -2.0 * ((P[Pp] - geo.Cc[Ci]) * u).sum(1)
        ok = np.abs(t) > 1e-6 * geo.scale
        X = P[Pp] + t[:, None] * u
        sel = np.nonzero(ok)[0]
        Li, Ci, Pp, X = Li[sel], Ci[sel], Pp[sel], X[sel]
        yield ("line_circle", X,
               lambda k: f"{geo.line_text(int(Li[k]), int(Pp[k]))}, {geo.circle_text(int(Ci[k]), int(Pp[k]))}",
               Li, Ci, None, None)

    # 2b. two circles through a common configuration point
    pairs = []
    for p in range(n):
        cs = geo.point_circles[p]
        for a in range(len(cs)):
            for b in range(a + 1, len(cs)):
                pairs.append((cs[a], cs[b], p))
    if len(pairs) > MAX_ROWS:
        pairs = [pairs[k] for k in sorted(rng.sample(range(len(pairs)), MAX_ROWS))]
    if pairs:
        C1 = np.array([q[0] for q in pairs])
        C2 = np.array([q[1] for q in pairs])
        Pp = np.array([q[2] for q in pairs])
        o1, o2 = geo.Cc[C1], geo.Cc[C2]
        dv = o2 - o1
        dd = (dv**2).sum(1)
        ok = dd > (1e-6 * geo.scale) ** 2
        dd = np.where(ok, dd, 1.0)
        proj = o1 + (((P[Pp] - o1) * dv).sum(1) / dd)[:, None] * dv
        X = 2 * proj - P[Pp]
        ok &= np.linalg.norm(X - P[Pp], axis=1) > 1e-6 * geo.scale
        sel = np.nonzero(ok)[0]
        C1, C2, Pp, X = C1[sel], C2[sel], Pp[sel], X[sel]
        yield ("circle_circle", X,
               lambda k: f"{geo.circle_text(int(C1[k]), int(Pp[k]))}, {geo.circle_text(int(C2[k]), int(Pp[k]))}",
               None, C1, C2, None)


def heuristic_pool(geo: Geo, rng, require_favorable: bool = True) -> list[dict]:
    """All favourable basic constructions, grouped by the point they define."""
    groups: dict = {}
    q = 1e-6 * geo.scale
    for cat, X, body, exL, exC1, exC2, foot_pt in _blocks(geo, rng):
        if len(X) == 0:
            continue
        valid = np.nonzero(geo.acceptable_mask(X))[0]
        for start in range(0, len(valid), CHUNK):
            idx = valid[start:start + CHUNK]
            Xc = X[idx]
            Lm, Cm = geo.incidence(Xc)
            r = np.arange(len(idx))
            if cat in ("midpoint", "mirror", "foot", "line_line", "line_circle"):
                Lm[r, exL[idx]] = False
            if cat == "line_line":
                Lm[r, exC1[idx]] = False  # second line
            if cat in ("line_circle", "circle_circle"):
                Cm[r, exC1[idx]] = False
            if cat == "circle_circle":
                Cm[r, exC2[idx]] = False
            if cat == "foot":
                Lm &= ~geo.PL[foot_pt[idx]]
                Cm[:] = False
            count = Lm.sum(1) + Cm.sum(1)
            ks = np.nonzero(count >= 1)[0] if require_favorable else range(len(idx))
            for k in ks:
                xy = Xc[k]
                key = (int(round(xy[0] / q)), int(round(xy[1] / q)))
                g = groups.get(key)
                if g is None:
                    g = groups[key] = {"xy": xy, "reps": [], "count": 0}
                g["reps"].append((PRIORITY[cat], cat, body(int(idx[k]))))
                g["count"] = max(g["count"], int(count[k]))
    pool = []
    for key in sorted(groups):
        g = groups[key]
        g["reps"].sort()
        pool.append(g)
    return pool


def full_pool(geo: Geo, rng, require_favorable: bool = True, random_share: float = 0.25) -> list[dict]:
    """Heuristic categories 1-5 plus the paper's random-construction category."""
    pool = heuristic_pool(geo, rng, require_favorable)
    n_random = max(2, int(len(pool) * random_share))
    for _ in range(n_random):
        res = random_construction(geo, rng)
        if res is not None:
            pool.append({"xy": res[0], "reps": [(9, "random", res[1])], "count": 0})
    return pool
