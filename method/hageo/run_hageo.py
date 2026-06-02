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
import numericals as nm  # type: ignore  # noqa: E402
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
    solved, status, seconds, _ = run_ddar_state(problem_id, statement, defs, rules, timeout)
    return solved, status, seconds


def run_ddar_state(
    problem_id: str,
    statement: str,
    defs: dict,
    rules: dict,
    timeout: int,
) -> tuple[bool, str, float, gh.Graph | None]:
    start = time.time()
    g: gh.Graph | None = None
    try:
        with hard_timeout(timeout):
            p = parse_problem(problem_id, statement)
            g, _ = gh.Graph.build_problem(p, defs, verbose=False)
            ddar.solve(g, rules, p, max_level=1000, timeout=timeout)
            goal_args = g.names2nodes(p.goal.args)
            solved = bool(g.check(p.goal.name, goal_args))
        return solved, "solved" if solved else "failed", time.time() - start, g
    except DDARTimeout:
        return False, "timeout", time.time() - start, g
    except Exception as exc:  # DDAR can reject numerically degenerate drawings.
        return False, f"error:{type(exc).__name__}:{exc}", time.time() - start, None


def insert_aux(statement: str, aux_clauses: list[str]) -> str:
    setup, goal = statement.split(" ? ", 1)
    return setup + "; " + "; ".join(aux_clauses) + " ? " + goal


def point_names(statement: str) -> list[str]:
    """Return declared point symbols in construction order.

    AlphaGeometry clauses declare constructed points on the left-hand side.
    The right-hand side also contains predicate names such as ``on_line`` and
    ``triangle``; treating those as points pollutes HAGeo's auxiliary search.
    """
    setup = statement.split(" ? ", 1)[0]
    names: list[str] = []
    for clause in setup.split("; "):
        lhs = clause.split(" = ", 1)[0].strip()
        for name in lhs.split():
            if name and name not in names:
                names.append(name)
    return names


def pair_lines(points: list[str]) -> list[tuple[str, str]]:
    return [(a, b) for a, b in itertools.combinations(points, 2)]


def _coord_name(prefix: str, index: int, point: nm.Point) -> tuple[str, str]:
    arg_name = f"{prefix}{index}"
    declared_name = f"{arg_name}@{point.x:.12g}_{point.y:.12g}"
    return declared_name, arg_name


def _close_point(a: nm.Point, b: nm.Point, tol: float = 1e-7) -> bool:
    return a.distance(b) <= tol


def _is_known_point(point: nm.Point, known: list[gh.Point]) -> bool:
    return any(_close_point(point, p.num) for p in known)


def _dedupe_key(point: nm.Point, clauses: list[str]) -> tuple[int, int, tuple[str, ...]]:
    return (round(point.x * 1e8), round(point.y * 1e8), tuple(sorted(clauses)))


def _line_records(points: list[gh.Point]) -> list[tuple[str, str, nm.Line]]:
    records = []
    for a, b in itertools.combinations(points, 2):
        if _close_point(a.num, b.num):
            continue
        records.append((a.name, b.name, nm.Line(a.num, b.num)))
    return records


def _circle_records(points: list[gh.Point]) -> list[tuple[str, str, nm.Circle]]:
    records = []
    for o, r in itertools.permutations(points, 2):
        if _close_point(o.num, r.num):
            continue
        records.append((o.name, r.name, nm.Circle(o.num, p1=r.num)))
    return records


def _line_incidence(point: nm.Point, lines: list[tuple[str, str, nm.Line]]) -> list[str]:
    out = []
    for a, b, line in lines:
        if point.distance(line) <= 1e-7:
            out.append(f"on_line {{x}} {a} {b}")
    return out


def _circle_incidence(point: nm.Point, circles: list[tuple[str, str, nm.Circle]]) -> list[str]:
    out = []
    for o, r, circle in circles:
        if point.distance(circle) <= 1e-7:
            out.append(f"on_circle {{x}} {o} {r}")
    return out


def _same_line_clause(clause: str, a: str, b: str) -> bool:
    return f" {a} {b}" in clause or f" {b} {a}" in clause


def _same_circle_clause(clause: str, o: str, r: str) -> bool:
    return clause.endswith(f" {o} {r}")


def _materialize_candidates(
    buckets: list[list[tuple[nm.Point, list[str]]]],
    max_candidates: int,
) -> list[str]:
    candidates: list[str] = []
    seen = set()
    counter = 0
    for grouped in itertools.zip_longest(*buckets):
        for item in grouped:
            if item is None:
                continue
            point, clauses = item
            key = _dedupe_key(point, clauses)
            if key in seen:
                continue
            seen.add(key)
            declared_name, arg_name = _coord_name("x", counter, point)
            candidates.append(
                f"{declared_name} = " + ", ".join(c.format(x=arg_name) for c in clauses)
            )
            counter += 1
            if len(candidates) >= max_candidates:
                return candidates
    return candidates


def random_construction_items_from_graph(
    graph: gh.Graph, max_candidates: int
) -> list[tuple[nm.Point, list[str]]]:
    """Broad valid basic-construction pool used for random auxiliary search."""
    pts = sorted(graph.all_points(), key=lambda p: p.name)
    lines = _line_records(pts)
    circles = _circle_records(pts)
    bucket: list[tuple[nm.Point, list[str]]] = []

    def add(point: nm.Point, clauses: list[str]) -> None:
        if len(bucket) >= max_candidates * 4 or _is_known_point(point, pts):
            return
        bucket.append((point, clauses))

    for (a, b, lab), (c, d, lcd) in itertools.combinations(lines, 2):
        if len({a, b, c, d}) < 4 or lab.is_parallel(lcd):
            continue
        try:
            add(nm.line_line_intersection(lab, lcd), [f"on_line {{x}} {a} {b}", f"on_line {{x}} {c} {d}"])
        except nm.InvalidLineIntersectError:
            continue
        if len(bucket) >= max_candidates * 4:
            break

    for a, b, line in lines:
        for o, r, circle in circles[: max_candidates * 8]:
            if len({a, b, o, r}) < 3:
                continue
            try:
                for x in nm.line_circle_intersection(line, circle):
                    add(x, [f"on_line {{x}} {a} {b}", f"on_circle {{x}} {o} {r}"])
            except nm.InvalidQuadSolveError:
                continue
            if len(bucket) >= max_candidates * 4:
                break
        if len(bucket) >= max_candidates * 4:
            break

    for (o1, r1, c1), (o2, r2, c2) in itertools.combinations(circles[: max_candidates * 8], 2):
        if len({o1, r1, o2, r2}) < 3:
            continue
        try:
            for x in nm.circle_circle_intersection(c1, c2):
                add(x, [f"on_circle {{x}} {o1} {r1}", f"on_circle {{x}} {o2} {r2}"])
        except nm.InvalidQuadSolveError:
            continue
        if len(bucket) >= max_candidates * 4:
            break

    for a, b in itertools.combinations(pts, 2):
        add(a.num.midpoint(b.num), [f"midpoint {{x}} {a.name} {b.name}"])

    for a, b in itertools.permutations(pts, 2):
        add(b.num * 2.0 - a.num, [f"mirror {{x}} {a.name} {b.name}"])
        if len(bucket) >= max_candidates * 4:
            break

    for p in pts:
        for a, b, line in lines:
            if p.name in (a, b) or p.num.distance(line) <= 1e-7:
                continue
            add(p.num.foot(line), [f"foot {{x}} {p.name} {a} {b}"])
        if len(bucket) >= max_candidates * 4:
            break

    return bucket[:max_candidates]


def identical_point_items_from_graph(
    graph: gh.Graph, max_candidates: int
) -> list[tuple[nm.Point, list[str]]]:
    """Existing points that can be reintroduced as multi-object intersections.

    The HAGeo paper includes a special identical-point heuristic: when a known
    point is numerically the intersection of multiple already-available objects,
    adding a new construction for that same location can expose the useful
    incidence path to DDAR. AlphaGeometry's upstream engine does not include
    HAGeo's optimized identical-point support, so downstream DDAR calls may
    reject some of these candidates; those failures are handled by run_ddar().
    """
    pts = sorted(graph.all_points(), key=lambda p: p.name)
    lines = _line_records(pts)
    circles = _circle_records(pts)
    bucket: list[tuple[nm.Point, list[str]]] = []
    seen: set[tuple[int, int, tuple[str, ...]]] = set()

    for p in pts:
        incidences = [
            f"on_line {{x}} {a} {b}"
            for a, b, line in lines
            if p.name not in (a, b) and p.num.distance(line) <= 1e-7
        ]
        incidences += [
            f"on_circle {{x}} {o} {r}"
            for o, r, circle in circles
            if p.name not in (o, r) and p.num.distance(circle) <= 1e-7
        ]
        if len(incidences) < 2:
            continue
        for clauses in itertools.combinations(incidences[:8], 2):
            item = (p.num, list(clauses))
            key = _dedupe_key(*item)
            if key in seen:
                continue
            seen.add(key)
            bucket.append(item)
            if len(bucket) >= max_candidates:
                return bucket
    return bucket


def random_construction_candidates_from_graph(graph: gh.Graph, max_candidates: int) -> list[str]:
    """Materialized broad valid-construction pool for the random baseline."""
    return _materialize_candidates(
        [random_construction_items_from_graph(graph, max_candidates)], max_candidates
    )


def candidate_auxiliaries_from_graph(graph: gh.Graph, max_candidates: int) -> list[str]:
    """Generate the paper's numerically driven HAGeo auxiliary categories.

    HAGeo chooses basic constructions only when numerical computation shows
    that the new point has a favorable non-trivial incidence, such as lying on
    three or more lines/circles or a midpoint/foot/reflection lying on another
    object. The DDAR engine already relies on the same numeric diagram checks,
    so these clauses expose numerically verified construction facts rather than
    introducing neural or oracle proposals.
    """
    pts = sorted(graph.all_points(), key=lambda p: p.name)
    lines = _line_records(pts)
    circles = _circle_records(pts)
    buckets: list[list[tuple[nm.Point, list[str]]]] = [[] for _ in range(8)]

    def add(bucket: int, point: nm.Point, clauses: list[str]) -> None:
        if len(buckets[bucket]) >= max_candidates or _is_known_point(point, pts):
            return
        buckets[bucket].append((point, clauses[:4]))

    # 1. Intersections where at least three lines concur.
    for (a, b, lab), (c, d, lcd) in itertools.combinations(lines, 2):
        if len({a, b, c, d}) < 4 or lab.is_parallel(lcd):
            continue
        try:
            x = nm.line_line_intersection(lab, lcd)
        except nm.InvalidLineIntersectError:
            continue
        incidences = _line_incidence(x, lines)
        extras = [
            inc
            for inc in incidences
            if not _same_line_clause(inc, a, b) and not _same_line_clause(inc, c, d)
        ]
        if extras:
            add(0, x, [f"on_line {{x}} {a} {b}", f"on_line {{x}} {c} {d}"] + extras[:2])
        if len(buckets[0]) >= max_candidates:
            break

    # 2. Intersections supported by at least three lines/circles.
    for a, b, line in lines:
        for o, r, circle in circles[: max_candidates * 8]:
            if len({a, b, o, r}) < 3:
                continue
            try:
                xs = nm.line_circle_intersection(line, circle)
            except nm.InvalidQuadSolveError:
                continue
            for x in xs:
                incidences = _line_incidence(x, lines) + _circle_incidence(x, circles[: max_candidates * 8])
                extras = [
                    inc
                    for inc in incidences
                    if not _same_line_clause(inc, a, b) and not _same_circle_clause(inc, o, r)
                ]
                if extras:
                    add(1, x, [f"on_line {{x}} {a} {b}", f"on_circle {{x}} {o} {r}"] + extras[:2])
            if len(buckets[1]) >= max_candidates:
                break
        if len(buckets[1]) >= max_candidates:
            break

    for (o1, r1, c1), (o2, r2, c2) in itertools.combinations(circles[: max_candidates * 8], 2):
        if len({o1, r1, o2, r2}) < 3:
            continue
        try:
            xs = nm.circle_circle_intersection(c1, c2)
        except nm.InvalidQuadSolveError:
            continue
        for x in xs:
            incidences = _line_incidence(x, lines) + _circle_incidence(x, circles[: max_candidates * 8])
            extras = [
                inc
                for inc in incidences
                if not _same_circle_clause(inc, o1, r1) and not _same_circle_clause(inc, o2, r2)
            ]
            if extras:
                add(2, x, [f"on_circle {{x}} {o1} {r1}", f"on_circle {{x}} {o2} {r2}"] + extras[:2])
        if len(buckets[2]) >= max_candidates:
            break

    # 3-5. Midpoints, point reflections, and perpendicular feet that also lie
    # on another line/circle non-trivially.
    for a, b in itertools.combinations(pts, 2):
        x = a.num.midpoint(b.num)
        extras = [i for i in _line_incidence(x, lines) if f" {a.name} {b.name}" not in i and f" {b.name} {a.name}" not in i]
        extras += _circle_incidence(x, circles[: max_candidates * 8])
        if extras:
            add(3, x, [f"midpoint {{x}} {a.name} {b.name}", extras[0]])

    for a, b in itertools.permutations(pts, 2):
        x = b.num * 2.0 - a.num
        extras = [i for i in _line_incidence(x, lines) if f" {a.name} {b.name}" not in i and f" {b.name} {a.name}" not in i]
        extras += _circle_incidence(x, circles[: max_candidates * 8])
        if extras:
            add(4, x, [f"mirror {{x}} {a.name} {b.name}", extras[0]])
        if len(buckets[4]) >= max_candidates:
            break

    for p in pts:
        for a, b, line in lines:
            if p.name in (a, b) or p.num.distance(line) <= 1e-7:
                continue
            x = p.num.foot(line)
            extras = [i for i in _line_incidence(x, lines) if f" {a} {b}" not in i and f" {b} {a}" not in i]
            extras += _circle_incidence(x, circles[: max_candidates * 8])
            if extras:
                add(5, x, [f"foot {{x}} {p.name} {a} {b}", extras[0]])
        if len(buckets[5]) >= max_candidates:
            break

    # 6. Identical-point constructions are part of the paper's HAGeo heuristic.
    buckets[6].extend(identical_point_items_from_graph(graph, max_candidates))

    # 7. Random constructions are part of HAGeo's candidate universe, but are
    # intentionally placed after numerically favorable candidates.
    buckets[7].extend(random_construction_items_from_graph(graph, max_candidates))

    return _materialize_candidates(buckets, max_candidates)


def setup_graph(statement: str, defs: dict) -> gh.Graph:
    """Build only the construction graph; the theorem goal is irrelevant here."""
    setup = statement.split(" ? ", 1)[0]
    names = point_names(statement)
    if len(names) >= 2:
        dummy_goal = f"coll {names[0]} {names[1]} {names[0]}"
    elif names:
        dummy_goal = f"cong {names[0]} {names[0]} {names[0]} {names[0]}"
    else:
        raise ValueError("cannot build candidate graph without declared points")
    p = parse_problem("candidate_generation", f"{setup} ? {dummy_goal}")
    g, _ = gh.Graph.build_problem(p, defs, verbose=False)
    return g


def random_construction_candidates(statement: str, defs: dict, max_candidates: int) -> list[str]:
    g = setup_graph(statement, defs)
    return random_construction_candidates_from_graph(g, max_candidates)


def candidate_auxiliaries(statement: str, defs: dict, max_candidates: int) -> list[str]:
    g = setup_graph(statement, defs)
    return candidate_auxiliaries_from_graph(g, max_candidates)


def attempt_order(candidates: list[str], attempts: int, rng: random.Random) -> list[str]:
    """Interleave ranked heuristic candidates with shuffled exploration.

    HAGeo is a heuristic search procedure rather than a single greedy choice.
    Keeping only the first K ranked candidates can miss the paper's random
    construction category, so each budget gets both early high-priority
    candidates and broad valid-construction exploration.
    """
    ranked = candidates[: min(len(candidates), attempts)]
    shuffled = candidates[:]
    rng.shuffle(shuffled)
    ordered: list[str] = []
    seen: set[str] = set()
    for ranked_candidate, shuffled_candidate in itertools.zip_longest(ranked, shuffled):
        for candidate in (ranked_candidate, shuffled_candidate):
            if candidate is None or candidate in seen:
                continue
            ordered.append(candidate)
            seen.add(candidate)
            if len(ordered) >= attempts:
                return ordered
    return ordered


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
    solved, status, seconds, graph = run_ddar_state(problem_id, statement, defs, rules, timeout)
    result = {
        "problem_id": problem_id,
        "source": row.get("source", ""),
        "difficulty": row.get("difficulty"),
        "solved": solved,
        "attempt_index": 0,
        "attempt_budget": attempts,
        "rounds": rounds,
        "timeout_seconds": timeout,
        "neural_inference_used": 0,
        "auxiliary_clauses": [],
        "status": "ddar_" + status,
        "seconds": seconds,
    }
    if solved:
        return result

    if graph is not None:
        candidates = candidate_auxiliaries_from_graph(graph, max_candidates=max(128, attempts * rounds * 4))
    else:
        candidates = candidate_auxiliaries(statement, defs, max_candidates=max(128, attempts * rounds * 4))
    rng = random.Random(seed)

    total_seconds = seconds
    for idx in range(1, attempts + 1):
        candidate_statement = statement
        aux = []
        for round_index in range(rounds):
            round_candidates = candidates
            if round_index > 0:
                try:
                    round_candidates = candidate_auxiliaries(
                        candidate_statement,
                        defs,
                        max_candidates=max(128, attempts * rounds),
                    )
                except Exception:
                    round_candidates = []
            if not round_candidates:
                break
            ordered = attempt_order(round_candidates, attempts, rng)
            chosen = ordered[(idx - 1) % len(ordered)]
            aux.append(chosen)
            candidate_statement = insert_aux(candidate_statement, [chosen])
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
        if not aux:
            break
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
