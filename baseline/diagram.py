"""Numerical configuration helpers for the random auxiliary-construction baseline (copy of method/hageo/diagram.py so the baseline never depends on method/).

A configuration is a list of named points with coordinates (the evaluator
supplies a drawing of each problem).  Lines are taken through pairs of points
and circles through triples of points or centred at a point through another
point, deduplicated by the set of points they contain.
"""

from __future__ import annotations

import itertools

import numpy as np


class Geo:
    def __init__(self, names: list[str], coords):
        self.names = list(names)
        self.P = np.asarray(coords, dtype=float).reshape(-1, 2)
        self.n = len(self.names)
        diff = self.P[:, None, :] - self.P[None, :, :]
        dist = np.sqrt((diff**2).sum(-1))
        self.scale = float(dist.max()) if self.n > 1 else 1.0
        self.tol = 1e-7 * max(self.scale, 1e-9)
        avg = self.P.mean(axis=0)
        to_avg = np.linalg.norm(self.P - avg, axis=1)
        # AlphaGeometry rejects new points closer than 0.1 * min(|p - avg|)
        # to an existing point, or farther than 4 * max(|p - avg|) from avg.
        self.close_thr = 0.1 * float(to_avg.min()) if self.n else 0.0
        self.far_center = avg
        self.far_thr = 4.0 * float(to_avg.max()) if self.n else np.inf
        self._build_lines()
        self._build_circles()

    # ------------------------------------------------------------------
    def add(self, name: str, xy) -> "Geo":
        return Geo(self.names + [name], np.vstack([self.P, np.asarray(xy, float)[None, :]]))

    def acceptable(self, xy) -> bool:
        xy = np.asarray(xy, float)
        if not np.all(np.isfinite(xy)):
            return False
        if self.n and np.min(np.linalg.norm(self.P - xy, axis=1)) < max(self.close_thr, 10 * self.tol):
            return False
        if np.linalg.norm(xy - self.far_center) > self.far_thr:
            return False
        return True

    def acceptable_mask(self, X: np.ndarray) -> np.ndarray:
        ok = np.all(np.isfinite(X), axis=1)
        Xs = np.where(ok[:, None], X, 0.0)
        d = np.sqrt(((Xs[:, None, :] - self.P[None, :, :]) ** 2).sum(-1)).min(axis=1)
        ok &= d >= max(self.close_thr, 10 * self.tol)
        ok &= np.linalg.norm(Xs - self.far_center, axis=1) <= self.far_thr
        return ok

    # ------------------------------------------------------------------
    def _build_lines(self) -> None:
        normals, offsets, pts, reps = [], [], [], []
        seen_index: dict = {}
        self.pair_line = {}
        for i, j in itertools.combinations(range(self.n), 2):
            v = self.P[j] - self.P[i]
            length = float(np.hypot(*v))
            if length <= 10 * self.tol:
                continue
            nv = np.array([-v[1], v[0]]) / length
            c = float(nv @ self.P[i])
            on = tuple(int(k) for k in np.nonzero(np.abs(self.P @ nv - c) <= self.tol)[0])
            if on in seen_index:
                self.pair_line[(i, j)] = seen_index[on]
                continue
            seen_index[on] = len(normals)
            self.pair_line[(i, j)] = len(normals)
            normals.append(nv)
            offsets.append(c)
            pts.append(frozenset(on))
            reps.append((on[0], on[1]))
        self.Ln = np.array(normals, dtype=float).reshape(-1, 2)
        self.Lc = np.array(offsets, dtype=float)
        self.Lpts = pts
        self.Lrep = reps
        self.L = len(normals)
        self.point_lines = [[li for li in range(self.L) if p in self.Lpts[li]] for p in range(self.n)]
        self.PL = np.zeros((self.n, self.L), dtype=bool)
        for li, s in enumerate(self.Lpts):
            for p in s:
                self.PL[p, li] = True

    def line_of(self, i: int, j: int) -> int:
        return self.pair_line[(min(i, j), max(i, j))]

    def _build_circles(self) -> None:
        centers, radii, pts, center_idx = [], [], [], []
        index = {}

        def register(cen, r, center_point):
            on = tuple(
                int(k) for k in np.nonzero(np.abs(np.linalg.norm(self.P - cen, axis=1) - r) <= self.tol)[0]
            )
            if len(on) >= 3:
                key = ("set", on)
            else:
                key = ("center", center_point, on)
            if key in index:
                ci = index[key]
                if center_idx[ci] is None and center_point is not None:
                    center_idx[ci] = center_point
                return
            index[key] = len(centers)
            centers.append(np.asarray(cen, float))
            radii.append(float(r))
            pts.append(frozenset(on))
            center_idx.append(center_point)

        for i, j, k in itertools.combinations(range(self.n), 3):
            a, b, c = self.P[i], self.P[j], self.P[k]
            d = 2.0 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
            if abs(d) <= 1e-9 * self.scale**2:
                continue
            a2, b2, c2 = a @ a, b @ b, c @ c
            ux = (a2 * (b[1] - c[1]) + b2 * (c[1] - a[1]) + c2 * (a[1] - b[1])) / d
            uy = (a2 * (c[0] - b[0]) + b2 * (a[0] - c[0]) + c2 * (b[0] - a[0])) / d
            cen = np.array([ux, uy])
            r = float(np.linalg.norm(a - cen))
            if r > 50 * self.scale:
                continue
            hit = np.nonzero(np.linalg.norm(self.P - cen, axis=1) <= self.tol)[0]
            register(cen, r, int(hit[0]) if len(hit) else None)
        for o, a in itertools.permutations(range(self.n), 2):
            r = float(np.linalg.norm(self.P[a] - self.P[o]))
            if r <= 10 * self.tol:
                continue
            register(self.P[o], r, o)
        self.Cc = np.array(centers, dtype=float).reshape(-1, 2)
        self.Cr = np.array(radii, dtype=float)
        self.Cpts = pts
        self.Ccenter = center_idx
        self.C = len(centers)
        self.point_circles = [[ci for ci in range(self.C) if p in self.Cpts[ci]] for p in range(self.n)]

    # ------------------------------------------------------------------
    def incidence(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Boolean (m, L) and (m, C) incidence of points X on lines / circles."""
        if len(X) == 0:
            return np.zeros((0, self.L), bool), np.zeros((0, self.C), bool)
        Lm = np.abs(X @ self.Ln.T - self.Lc[None, :]) <= self.tol
        x2 = (X**2).sum(1)[:, None]
        c2 = (self.Cc**2).sum(1)[None, :]
        d2 = x2 + c2 - 2.0 * (X @ self.Cc.T)
        d = np.sqrt(np.maximum(d2, 0.0))
        Cm = np.abs(d - self.Cr[None, :]) <= self.tol
        return Lm, Cm

    # ------------------------------------------------------------------
    def line_text(self, li: int, through: int | None = None) -> str:
        a, b = self.Lrep[li]
        if through is not None and through in self.Lpts[li]:
            other = min(p for p in self.Lpts[li] if p != through)
            a, b = through, other
        return f"on_line {{x}} {self.names[a]} {self.names[b]}"

    def circle_text(self, ci: int, through: int) -> str:
        on = sorted(self.Cpts[ci])
        if len(on) >= 3:
            others = [p for p in on if p != through][:2]
            return f"on_circum {{x}} {self.names[through]} {self.names[others[0]]} {self.names[others[1]]}"
        o = self.Ccenter[ci]
        return f"on_circle {{x}} {self.names[o]} {self.names[through]}"


# ----------------------------------------------------------------------
# Random basic constructions ("randomly perform an action over a random set
# of geometry objects").

ACTIONS = (
    "midpoint",
    "mirror",
    "foot",
    "line_line",
    "line_circle",
    "circle_circle",
    "circumcenter",
    "orthocenter",
    "incenter",
    "reflect",
    "perp_line",
    "para_line",
)


def _collinear(geo: Geo, a, b, c) -> bool:
    u, v = geo.P[b] - geo.P[a], geo.P[c] - geo.P[a]
    return abs(u[0] * v[1] - u[1] * v[0]) <= 1e-6 * geo.scale**2


def _circum(geo: Geo, a, b, c):
    A, B, C = geo.P[a], geo.P[b], geo.P[c]
    d = 2.0 * (A[0] * (B[1] - C[1]) + B[0] * (C[1] - A[1]) + C[0] * (A[1] - B[1]))
    a2, b2, c2 = A @ A, B @ B, C @ C
    ux = (a2 * (B[1] - C[1]) + b2 * (C[1] - A[1]) + c2 * (A[1] - B[1])) / d
    uy = (a2 * (C[0] - B[0]) + b2 * (A[0] - C[0]) + c2 * (B[0] - A[0])) / d
    return np.array([ux, uy])


def _line_intersection(p1, p2, p3, p4):
    d1, d2 = p2 - p1, p4 - p3
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) <= 1e-9 * (np.linalg.norm(d1) * np.linalg.norm(d2) + 1e-300):
        return None
    t = ((p3[0] - p1[0]) * d2[1] - (p3[1] - p1[1]) * d2[0]) / den
    return p1 + t * d1


def _foot(p, a, b):
    d = b - a
    return a + ((p - a) @ d) / (d @ d) * d


def random_action(geo: Geo, rng, action: str):
    n = geo.n
    N = geo.names
    P = geo.P
    if n < 3:
        return None
    pick = lambda k: rng.sample(range(n), k)  # noqa: E731
    if action == "midpoint":
        a, b = pick(2)
        return (P[a] + P[b]) / 2, f"midpoint {{x}} {N[a]} {N[b]}"
    if action == "mirror":
        a, b = pick(2)
        return 2 * P[b] - P[a], f"mirror {{x}} {N[a]} {N[b]}"
    if action == "foot":
        a, b, c = pick(3)
        if _collinear(geo, a, b, c):
            return None
        return _foot(P[a], P[b], P[c]), f"foot {{x}} {N[a]} {N[b]} {N[c]}"
    if action == "reflect":
        a, b, c = pick(3)
        if _collinear(geo, a, b, c):
            return None
        return 2 * _foot(P[a], P[b], P[c]) - P[a], f"reflect {{x}} {N[a]} {N[b]} {N[c]}"
    if action in ("circumcenter", "orthocenter", "incenter"):
        a, b, c = pick(3)
        if _collinear(geo, a, b, c):
            return None
        A, B, C = P[a], P[b], P[c]
        if action == "circumcenter":
            xy = _circum(geo, a, b, c)
        elif action == "orthocenter":
            xy = A + B + C - 2 * _circum(geo, a, b, c)
        else:
            la, lb, lc = np.linalg.norm(B - C), np.linalg.norm(C - A), np.linalg.norm(A - B)
            xy = (la * A + lb * B + lc * C) / (la + lb + lc)
        return xy, f"{action} {{x}} {N[a]} {N[b]} {N[c]}"
    if action == "line_line":
        if n < 4:
            return None
        a, b, c, d = pick(4)
        xy = _line_intersection(P[a], P[b], P[c], P[d])
        if xy is None:
            return None
        return xy, f"on_line {{x}} {N[a]} {N[b]}, on_line {{x}} {N[c]} {N[d]}"
    if action in ("perp_line", "para_line"):
        if n < 4:
            return None
        a, b, c = pick(3)
        d, e = rng.sample([i for i in range(n)], 2)
        if np.linalg.norm(P[b] - P[c]) <= 10 * geo.tol or (d, e) == (b, c):
            return None
        u = P[c] - P[b]
        direction = np.array([-u[1], u[0]]) if action == "perp_line" else u
        xy = _line_intersection(P[a], P[a] + direction, P[d], P[e])
        if xy is None:
            return None
        if action == "para_line" and _collinear(geo, a, b, c):
            return None
        kind = "on_tline" if action == "perp_line" else "on_pline"
        return xy, f"{kind} {{x}} {N[a]} {N[b]} {N[c]}, on_line {{x}} {N[d]} {N[e]}"
    if action == "line_circle":
        p, a, b, c = pick(4)
        if _collinear(geo, p, b, c):
            return None
        cen = _circum(geo, p, b, c)
        u = P[a] - P[p]
        u = u / np.linalg.norm(u)
        t = -2.0 * (u @ (P[p] - cen))
        if abs(t) <= 1e-6 * geo.scale:
            return None
        return P[p] + t * u, f"on_line {{x}} {N[p]} {N[a]}, on_circum {{x}} {N[p]} {N[b]} {N[c]}"
    if action == "circle_circle":
        if n < 5:
            return None
        p, a, b, c, d = pick(5)
        if _collinear(geo, p, a, b) or _collinear(geo, p, c, d):
            return None
        c1, c2 = _circum(geo, p, a, b), _circum(geo, p, c, d)
        dv = c2 - c1
        if np.linalg.norm(dv) <= 1e-6 * geo.scale:
            return None
        proj = c1 + ((P[p] - c1) @ dv) / (dv @ dv) * dv
        xy = 2 * proj - P[p]
        if np.linalg.norm(xy - P[p]) <= 1e-6 * geo.scale:
            return None
        return xy, f"on_circum {{x}} {N[p]} {N[a]} {N[b]}, on_circum {{x}} {N[p]} {N[c]} {N[d]}"
    raise ValueError(action)


def random_construction(geo: Geo, rng, tries: int = 200):
    for _ in range(tries):
        res = random_action(geo, rng, rng.choice(ACTIONS))
        if res is not None and geo.acceptable(res[0]):
            return np.asarray(res[0], float), res[1]
    return None
