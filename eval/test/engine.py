"""Evaluator-owned DDAR verification (held-out test side).

Uses the AlphaGeometry DD+AR engine vendored in ``eval/test/ag``.  Every
solve the evaluator reports is established here: the original problem
statement (premises and goal held by the evaluator) plus the submitted
auxiliary clauses is drawn with a fixed seed and passed to DDAR under a fixed
per-attempt timeout.  Nothing a submission writes is trusted.
"""

from __future__ import annotations

import contextlib
import os
import random
import signal
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
AG_DIR = HERE / "ag"

_AG = None


def ag():
    """Import the vendored engine lazily (it pulls numpy and matplotlib)."""
    global _AG
    if _AG is None:
        os.environ.setdefault("MPLBACKEND", "Agg")
        os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl-eval")
        if str(AG_DIR) not in sys.path:
            sys.path.insert(0, str(AG_DIR))
        from absl import logging as absl_logging  # noqa: E402

        absl_logging.set_verbosity(absl_logging.ERROR)
        import numpy as np  # noqa: E402
        import ddar  # noqa: E402
        import graph as gh  # noqa: E402
        import numericals as nm  # noqa: E402
        import problem as pr  # noqa: E402

        defs = pr.Definition.from_txt_file(str(AG_DIR / "defs.txt"), to_dict=True)
        rules = pr.Theorem.from_txt_file(str(AG_DIR / "rules.txt"), to_dict=True)
        _AG = {"np": np, "ddar": ddar, "gh": gh, "nm": nm, "pr": pr, "defs": defs, "rules": rules}
    return _AG


class _Timeout(BaseException):
    """Not an Exception subclass, so no handler inside the engine can swallow it."""


@contextlib.contextmanager
def hard_timeout(seconds: float):
    """Limit on the process's CPU time, with a generous wall-clock backstop.

    CPU time (not wall-clock time) decides, so the verdict does not depend on
    how loaded the machine is or how many verifications run in parallel.
    """

    def _raise(_signum, _frame):
        raise _Timeout()

    prev_prof = signal.signal(signal.SIGPROF, _raise)
    prev_alrm = signal.signal(signal.SIGALRM, _raise)
    signal.setitimer(signal.ITIMER_PROF, max(0.01, float(seconds)))
    signal.setitimer(signal.ITIMER_REAL, max(0.01, 4.0 * float(seconds) + 60.0))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_PROF, 0)
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGPROF, prev_prof)
        signal.signal(signal.SIGALRM, prev_alrm)


def _seed_all(seed: int) -> None:
    A = ag()
    random.seed(seed)
    A["np"].random.seed(seed % (2**32))


def bounded_build(statement: str, seed: int, max_tries: int = 60):
    """AlphaGeometry's ``Graph.build_problem`` with a bounded redraw loop.

    Upstream retries forever when a construction can never be drawn (for
    example an auxiliary point that coincides with an existing one); here a
    construction that fails ``max_tries`` redraws makes the attempt fail.
    Returns (graph, problem) or (None, problem).
    """
    A = ag()
    gh, nm, pr = A["gh"], A["nm"], A["pr"]
    p = pr.Problem.from_txt(statement, translate=False)
    _seed_all(seed)
    for _ in range(max_tries):
        try:
            g = gh.Graph()
            added = []
            plevel = 0
            for clause in p.clauses:
                adds, plevel = g.add_clause(clause, plevel, A["defs"], verbose=False)
                added += adds
            g.plevel = plevel
        except (
            nm.InvalidLineIntersectError,
            nm.InvalidQuadSolveError,
            gh.DepCheckFailError,
            gh.PointTooCloseError,
            gh.PointTooFarError,
        ):
            continue
        if p.goal is not None:
            args = list(map(lambda x: g.get(x, lambda: int(x)), p.goal.args))
            if not nm.check(p.goal.name, args):
                continue
        g.url = p.url
        g.build_def = (p, A["defs"])
        for add in added:
            g.add_algebra(add, level=0)
        return g, p
    return None, p


def statement_with_aux(setup: str, goal: str, aux: list[str]) -> str:
    clauses = setup
    if aux:
        clauses = setup + "; " + "; ".join(aux)
    return f"{clauses} ? {goal}"


def draw_coordinates(setup: str, goal: str, seed: int, timeout: float = 120.0) -> dict | None:
    """Coordinates of the evaluator's drawing of the problem (given to proposers)."""
    try:
        with hard_timeout(timeout):
            g, _ = bounded_build(statement_with_aux(setup, goal, []), seed, max_tries=200)
    except _Timeout:
        return None
    except Exception:  # noqa: BLE001 - engine rejects some degenerate inputs
        return None
    if g is None:
        return None
    return {pt.name: [float(pt.num.x), float(pt.num.y)] for pt in g.all_points()}


def verify(setup: str, goal: str, aux: list[str], seed: int, timeout: float) -> tuple[str, float]:
    """Run DDAR on premises + auxiliaries.  Returns (status, cpu_seconds).

    status is one of ``solved``, ``saturated``, ``timeout``, ``unbuildable``,
    ``error``.  Only ``solved`` counts.  ``timeout`` is a CPU-time limit.
    """
    A = ag()
    started = time.process_time()
    try:
        with hard_timeout(timeout):
            g, p = bounded_build(statement_with_aux(setup, goal, aux), seed)
            if g is None:
                return "unbuildable", time.process_time() - started
            # The engine's own per-level timer is set far above the hard limit so
            # that only the evaluator's wall-clock limit ends a run (a level cut
            # short internally could otherwise be misread as saturation).
            A["ddar"].solve(g, A["rules"], p, max_level=1000, timeout=int(10 * timeout + 10))
            goal_args = g.names2nodes(p.goal.args)
            solved = bool(g.check(p.goal.name, goal_args))
        return ("solved" if solved else "saturated"), time.process_time() - started
    except _Timeout:
        return "timeout", time.process_time() - started
    except Exception as exc:  # noqa: BLE001
        return f"error:{type(exc).__name__}", time.process_time() - started
