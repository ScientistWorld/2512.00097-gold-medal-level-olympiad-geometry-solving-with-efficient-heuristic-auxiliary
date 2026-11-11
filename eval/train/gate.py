"""Validity gate for submitted auxiliary constructions (visible train side).

Pure Python, no AlphaGeometry import.  A proposal that breaks any rule here is
a constraint violation: the evaluator scores the whole run as failed.

An auxiliary clause introduces exactly one fresh point through constructions
whose total degrees of freedom are exactly two (one point-determining
construction, or two one-dimensional loci).  This forbids over-determined
clauses (which would smuggle an unproved incidence in as a premise), explicit
coordinates (``name@x_y``), redefinition of existing points, and constructions
outside the allowlist.
"""

from __future__ import annotations

import re

# Constructions that determine the new point on their own: name -> number of
# arguments after the new point.
POINT_CONSTRUCTIONS = {
    "midpoint": 2,
    "mirror": 2,
    "foot": 3,
    "circumcenter": 3,
    "incenter": 3,
    "excenter": 3,
    "orthocenter": 3,
    "reflect": 3,
    "eq_triangle": 2,
    "psquare": 2,
    "nsquare": 2,
    "shift": 3,
    "intersection_ll": 4,
    "intersection_lc": 3,
    "intersection_cc": 3,
    "intersection_lp": 5,
    "intersection_lt": 5,
    "intersection_pp": 6,
    "intersection_tt": 6,
}

# One-dimensional loci: exactly two of them define a point.
LOCUS_CONSTRUCTIONS = {
    "on_line": 2,
    "on_circle": 2,
    "on_tline": 3,
    "on_pline": 3,
    "on_bline": 2,
    "on_dia": 2,
    "on_circum": 3,
    "angle_bisector": 3,
    "angle_mirror": 3,
    "eqdistance": 3,
    "lc_tangent": 2,
    "on_aline": 5,
}

NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,15}$")
RESERVED = set(POINT_CONSTRUCTIONS) | set(LOCUS_CONSTRUCTIONS) | {
    "free", "triangle", "segment", "on_opline", "s_angle", "eqangle3",
}


class GateError(ValueError):
    """A submitted proposal violates the auxiliary-construction rules."""


def setup_point_names(setup: str) -> list[str]:
    names: list[str] = []
    for clause in setup.split("; "):
        lhs = clause.split(" = ", 1)[0]
        for name in lhs.split():
            name = name.split("@", 1)[0]
            if name and name not in names:
                names.append(name)
    return names


def normalize_clause(clause: str, existing: set[str]) -> tuple[str, str]:
    """Validate one auxiliary clause and return (new_point, canonical_text).

    ``existing`` holds every point already defined (problem points plus
    earlier auxiliaries of the same attempt).
    """
    if not isinstance(clause, str):
        raise GateError(f"clause must be a string, got {type(clause).__name__}")
    if len(clause) > 400:
        raise GateError("clause too long")
    if "@" in clause or "?" in clause or ";" in clause or "\n" in clause:
        raise GateError(f"forbidden character in clause {clause!r}")
    text = " ".join(clause.split())
    if text.count(" = ") != 1:
        raise GateError(f"clause must have the form '<point> = <constructions>': {clause!r}")
    lhs, rhs = text.split(" = ", 1)
    lhs_names = lhs.split()
    if len(lhs_names) != 1:
        raise GateError(f"clause must introduce exactly one point: {clause!r}")
    x = lhs_names[0]
    if not NAME_RE.match(x) or x in RESERVED:
        raise GateError(f"invalid point name {x!r}")
    if x in existing:
        raise GateError(f"point {x!r} is not fresh")

    parts = [p.strip() for p in rhs.split(",")]
    if not parts or any(not p for p in parts):
        raise GateError(f"empty construction in {clause!r}")
    dof = 0
    canonical_parts = []
    kinds = []
    for part in parts:
        tokens = part.split()
        name, args = tokens[0], tokens[1:]
        if name in POINT_CONSTRUCTIONS:
            nargs = POINT_CONSTRUCTIONS[name]
            dof += 2
            kinds.append("point")
        elif name in LOCUS_CONSTRUCTIONS:
            nargs = LOCUS_CONSTRUCTIONS[name]
            dof += 1
            kinds.append("locus")
        else:
            raise GateError(f"construction {name!r} is not an allowed auxiliary construction")
        if len(args) == nargs + 1 and args[0] == x:
            args = args[1:]
        if len(args) != nargs:
            raise GateError(f"{name} expects {nargs} arguments after the new point: {part!r}")
        for arg in args:
            if arg == x:
                raise GateError(f"new point {x!r} used as an argument of its own definition")
            if arg not in existing:
                raise GateError(f"unknown point {arg!r} in {part!r}")
        canonical_parts.append(" ".join([name, x] + args))
    if dof != 2 or len(parts) > 2:
        raise GateError(
            f"clause must determine the point exactly (one point construction or two loci): {clause!r}"
        )
    return x, f"{x} = " + ", ".join(canonical_parts)


def validate_attempt(attempt, setup_names: list[str], max_aux: int) -> list[str]:
    if not isinstance(attempt, list):
        raise GateError("each attempt must be a list of clauses")
    if not 1 <= len(attempt) <= max_aux:
        raise GateError(f"each attempt must contain 1..{max_aux} clauses, got {len(attempt)}")
    existing = set(setup_names)
    out = []
    for clause in attempt:
        x, canonical = normalize_clause(clause, existing)
        existing.add(x)
        out.append(canonical)
    return out


def validate_rows(rows, problems: list[dict], max_attempts: int, max_aux: int) -> dict[str, list[list[str]]]:
    """Validate a proposer's full output; return canonical attempts per problem."""
    if not isinstance(rows, list):
        raise GateError("output must be a list of rows")
    expected = [p["problem_id"] for p in problems]
    by_id = {p["problem_id"]: p for p in problems}
    seen: dict[str, list[list[str]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise GateError("each output row must be a JSON object")
        pid = row.get("problem_id")
        if not isinstance(pid, str) or pid not in by_id:
            raise GateError(f"unknown problem_id {pid!r}")
        if pid in seen:
            raise GateError(f"duplicate row for {pid}")
        attempts = row.get("attempts")
        if not isinstance(attempts, list):
            raise GateError(f"{pid}: 'attempts' must be a list")
        if len(attempts) > max_attempts:
            raise GateError(f"{pid}: {len(attempts)} attempts exceed the budget of {max_attempts}")
        names = setup_point_names(by_id[pid]["setup"])
        seen[pid] = [validate_attempt(a, names, max_aux) for a in attempts]
    missing = [pid for pid in expected if pid not in seen]
    if missing:
        raise GateError(f"missing rows for {len(missing)} problems, e.g. {missing[:3]}")
    return seen
