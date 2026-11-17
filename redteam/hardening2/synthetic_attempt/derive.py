#!/usr/bin/env python3
"""Synthetic auxiliary-construction problems (evaluator-owned, held-out side).

Enlarges the test with many problems that provably need an auxiliary point,
following AlphaGeometry's synthetic-theorem recipe ("dependency difference"),
with every random choice drawn from a private salt so that no public file
holds the goals or the needed constructions:

``generate``  Draw a configuration: either a triangle followed by 4-7 random
    point definitions, or the premises of a cheap public HAGeo-409 / JGEX-231
    problem followed by 2-3 random point definitions.  Point definitions are
    drawn with the frequencies of the constructions in the two public
    benchmarks (circumcentre, intersection of two lines, foot, midpoint, second
    intersection with a circle, ...).  Run DDAR to saturation.  For every
    derived fact, the *setup* is the set of clauses its points depend on (for
    a public base, always the whole public statement); if DDAR cannot prove
    the fact from the setup alone but can once one (or two) of the removed
    random definitions is added back, the fact is a problem and those
    definitions are a known solution.

``select``  Keep a few problems per configuration, re-check each with the
    evaluator's own verifier (setup alone: DDAR saturates without the goal;
    setup + known solution: DDAR proves it), fix the per-attempt CPU limit from
    the measured times, store the evaluator's drawing, and split by
    configuration into the hidden test file and the visible train file.

The proposer sees the setup and a drawing; the goal and the known solution
stay here (the train file carries both).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing as mp
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

SALT = "hageo-gym-v3-synthetic-b82c92a5929afd33"
POOL = HERE / "synthetic_pool.jsonl"
TEST_OUT = HERE / "problems_synthetic.jsonl"
SOLUTIONS_OUT = HERE / "synthetic_solutions.jsonl"
SUMMARY_OUT = HERE / "synthetic_summary.json"
TRAIN_OUT = ROOT / "data" / "benchmarks" / "synthetic_train.jsonl"
SCREENS = (("hageo409", HERE / "screening.jsonl"), ("jgex", HERE / "screening_jgex.jsonl"))
EXISTING = {
    "test": (HERE / "problems.jsonl", HERE / "problems_jgex.jsonl"),
    "train": (ROOT / "data" / "benchmarks" / "hageo409_train.jsonl",
              ROOT / "data" / "benchmarks" / "jgex231_train.jsonl"),
}
PREDICATES = ("coll", "cyclic", "para", "perp", "cong", "midp", "eqangle", "eqratio")
AUX_NAMES = ("zz1", "zz2")
NAME_POOL = [chr(c) for c in range(ord("a"), ord("z") + 1)] + [
    f"{chr(c)}{i}" for i in range(1, 4) for c in range(ord("a"), ord("z") + 1)
]

# Point definitions, weighted by how often olympiad statements in HAGeo-409 /
# JGEX-231 define points this way.  All determinate forms are gate-legal
# auxiliary constructions; the two semi-free forms only appear in setups.
VOCAB = (
    ("circumcenter", 14), ("line_line", 13), ("foot", 12), ("midpoint", 10), ("line_circle", 10),
    ("circle_circle", 4), ("incenter", 4), ("tline_line", 4), ("orthocenter", 3), ("reflect", 3),
    ("pline_line", 3), ("mirror", 2), ("bisector_line", 2), ("bline_line", 2), ("tline_tline", 2),
    ("excenter", 1),
)
SEMI_FREE = (("on_line", 6), ("on_circum", 3))


def stable_int(*parts) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16)


def sample_clause(x: str, pts: list[str], rng: random.Random, semi_free: bool = False) -> tuple[str, str]:
    table = VOCAB + (SEMI_FREE if semi_free else ())
    kinds, weights = zip(*table)
    kind = rng.choices(kinds, weights)[0]
    s = lambda k: rng.sample(pts, k)  # noqa: E731
    if kind in ("circumcenter", "incenter", "excenter", "orthocenter"):
        a, b, c = s(3)
        body = f"{kind} {x} {a} {b} {c}"
    elif kind in ("midpoint", "mirror"):
        a, b = s(2)
        body = f"{kind} {x} {a} {b}"
    elif kind in ("foot", "reflect"):
        a, b, c = s(3)
        body = f"{kind} {x} {a} {b} {c}"
    elif kind == "line_line":
        a, b, c, d = s(4)
        body = f"on_line {x} {a} {b}, on_line {x} {c} {d}"
    elif kind == "line_circle":  # second intersection of a line with a circle through a common point
        if rng.random() < 0.5:
            a, b, c, d = s(4)
            body = f"on_circum {x} {a} {b} {c}, on_line {x} {a} {d}"
        else:
            o, a, d = s(3)
            body = f"on_circle {x} {o} {a}, on_line {x} {a} {d}"
    elif kind == "circle_circle":
        if rng.random() < 0.5 and len(pts) >= 5:
            a, b, c, d, e = s(5)
            body = f"on_circum {x} {a} {b} {c}, on_circum {x} {a} {d} {e}"
        else:
            o1, o2, a = s(3)
            body = f"on_circle {x} {o1} {a}, on_circle {x} {o2} {a}"
    elif kind in ("tline_line", "pline_line", "bisector_line"):
        a, b, c = s(3)
        d, e = s(2)
        name = {"tline_line": "on_tline", "pline_line": "on_pline", "bisector_line": "angle_bisector"}[kind]
        body = f"{name} {x} {a} {b} {c}, on_line {x} {d} {e}"
    elif kind == "bline_line":
        a, b = s(2)
        c, d = s(2)
        body = f"on_bline {x} {a} {b}, on_line {x} {c} {d}"
    elif kind == "tline_tline":
        a, b, c = s(3)
        d, e, f = s(3)
        body = f"on_tline {x} {a} {b} {c}, on_tline {x} {d} {e} {f}"
    elif kind == "on_line":
        a, b = s(2)
        body = f"on_line {x} {a} {b}"
    elif kind == "on_circum":
        a, b, c = s(3)
        body = f"on_circum {x} {a} {b} {c}"
    else:  # pragma: no cover
        raise ValueError(kind)
    return kind, f"{x} = {body}"


def clause_points(clause: str) -> tuple[list[str], set[str]]:
    """(points defined, point-like tokens referenced) of one clause."""
    lhs, rhs = clause.split(" = ", 1)
    defined = [n.split("@", 1)[0] for n in lhs.split()]
    refs = set()
    for part in rhs.split(","):
        for tok in part.split()[1:]:
            if tok not in defined:
                refs.add(tok)
    return defined, refs


def rename_token(clause: str, old: str, new: str) -> str:
    lhs, rhs = clause.split(" = ", 1)
    lhs = " ".join(new if t == old else t for t in lhs.split())
    parts = []
    for part in rhs.split(","):
        toks = part.split()
        parts.append(" ".join([toks[0]] + [new if t == old else t for t in toks[1:]]))
    return f"{lhs} = " + ", ".join(parts)


# --------------------------------------------------------------------------
# DDAR helpers (evaluator's engine)


def full_solve(A, g, p) -> list:
    """ddar.solve to saturation, also collecting the AR derivations it applies."""
    ddar, dd = A["ddar"], A["ddar"].dd
    level_times: list = []
    dervs, eq4 = g.derive_algebra(level=0, verbose=False)
    derives, eq4s, all_added = [dervs], [eq4], []
    while len(level_times) < 1000:
        dervs, eq4, _, added = ddar.saturate_or_goal(g, A["rules"], level_times, p, 1000, timeout=100000)
        all_added += added
        derives += dervs
        eq4s += eq4
        if not derives:
            break
        added = []
        while derives and not added:
            added += dd.apply_derivations(g, derives.pop(0))
        if added:
            all_added += added
            continue
        while eq4s and not added:
            added += dd.apply_derivations(g, eq4s.pop(0))
        all_added += added
        if not added:
            break
    return all_added


def saturate(engine, clauses: list[str], seed: int, cpu: float, max_tries: int = 25):
    """Draw + DDAR saturation.  Returns (graph or None, added deps, cpu seconds); raises engine._Timeout."""
    A = engine.ag()
    started = time.process_time()
    with engine.hard_timeout(cpu):
        g, p = engine.bounded_build("; ".join(clauses), seed, max_tries=max_tries)
        if g is None:
            return None, [], time.process_time() - started
        added = full_solve(A, g, p)
    return g, added, time.process_time() - started


# --------------------------------------------------------------------------
# generate


def build_config(engine, task: dict, rng: random.Random):
    """Returns (clauses, kinds, required clause indices) or None."""
    seed = task["seed"]
    if task["kind"] == "public":
        base = [c.strip() for c in task["setup"].split(";") if c.strip()]
        kinds = ["public"] * len(base)
        n_add = rng.choice((2, 3, 3))
        required = set(range(len(base)))
        semi = False
    else:
        names = NAME_POOL[:]
        rng.shuffle(names)
        a, b, c = names[:3]
        base = [f"{a} {b} {c} = triangle {a} {b} {c}"]
        kinds = ["triangle"]
        n_add = rng.randint(4, 7)
        required = {0}
        semi = True
    clauses = list(base)
    pts = []
    for cl in clauses:
        pts += clause_points(cl)[0]
    free_names = [n for n in NAME_POOL if n not in pts]
    rng.shuffle(free_names)
    for _ in range(n_add):
        x = free_names.pop()
        for _try in range(12):
            try:
                kind, cl = sample_clause(x, pts, rng, semi_free=semi)
            except ValueError:
                continue
            try:
                with engine.hard_timeout(5.0):
                    g, _ = engine.bounded_build("; ".join(clauses + [cl]), seed, max_tries=6)
            except engine._Timeout:
                g = None
            except Exception:  # noqa: BLE001
                g = None
            if g is not None:
                clauses.append(cl)
                kinds.append(kind)
                pts.append(x)
                break
    if len(clauses) - len(base) < (1 if task["kind"] == "public" else 3):
        return None
    return clauses, kinds, required


def process_config(task: dict) -> dict:
    import engine  # noqa: E402
    import gate  # noqa: E402

    A = engine.ag()
    nm = A["nm"]
    rng = random.Random(stable_int(SALT, "config", task["config_id"]))
    rec = {k: task[k] for k in ("config_id", "kind", "split", "seed", "source", "source_id")}
    rec["problems"] = []
    built = build_config(engine, task, rng)
    if built is None:
        rec["status"] = "unbuildable"
        return rec
    clauses, kinds, required = built
    rec.update(clauses=clauses, kinds=kinds)
    try:
        g_t, added, t_t = saturate(engine, clauses, task["seed"], task["cpu_full"])
    except engine._Timeout:
        rec["status"] = "timeout_full"
        return rec
    except Exception as exc:  # noqa: BLE001
        rec["status"] = f"error_full:{type(exc).__name__}"
        return rec
    if g_t is None:
        rec["status"] = "unbuildable_full"
        return rec
    rec["t_full"] = round(t_t, 3)

    # clause DAG
    defined_by, deps = {}, []
    for i, cl in enumerate(clauses):
        d, refs = clause_points(cl)
        for x in d:
            defined_by[x] = i
        deps.append({defined_by[r] for r in refs if r in defined_by})
    all_pts = set(defined_by)

    def closure(points) -> frozenset:
        todo = [defined_by[p] for p in points] + sorted(required)
        seen = set()
        while todo:
            i = todo.pop()
            if i not in seen:
                seen.add(i)
                todo += deps[i]
        return frozenset(seen)

    facts = {}
    for dep in added:
        if dep.name not in PREDICATES:
            continue
        args = [getattr(a, "name", None) for a in dep.args]
        if any(a not in all_pts for a in args):
            continue
        facts.setdefault((dep.name, tuple(args)), None)
    groups: dict = {}
    for name, args in facts:
        idx = closure(args)
        if len(idx) < len(clauses):
            groups.setdefault(idx, []).append((name, args))
    order = sorted(groups, key=lambda s: (len(clauses) - len(s), rng.random()))[: task["max_groups"]]
    rec["n_facts"] = len(facts)
    rec["n_groups"] = len(groups)
    for idx in order:
        setup = [clauses[i] for i in sorted(idx)]
        setup_pts = set()
        for cl in setup:
            setup_pts |= set(clause_points(cl)[0])
        try:
            g_a, _, t_a = saturate(engine, setup, task["seed"], task["cpu_part"])
        except (engine._Timeout, Exception):  # noqa: BLE001
            continue
        if g_a is None:
            continue
        cands = list(groups[idx])
        rng.shuffle(cands)
        open_facts = []
        try:
            with engine.hard_timeout(task["cpu_part"]):
                for name, args in cands[: task["checks_per_group"]]:
                    try:
                        pts_a = g_a.names2points(list(args))
                        if g_a.check(name, pts_a) or not nm.check(name, pts_a):
                            continue
                    except Exception:  # noqa: BLE001
                        continue
                    open_facts.append((name, args))
        except engine._Timeout:
            pass
        if not open_facts:
            continue
        removed = [i for i in range(len(clauses)) if i not in idx]

        def legal(cls: list[str]) -> list[str] | None:
            """Rename the removed points to fresh names and check the gate."""
            renamed = list(cls)
            for k, cl in enumerate(cls):
                x = clause_points(cl)[0][0]
                renamed = [rename_token(c, x, AUX_NAMES[k]) for c in renamed]
            existing = set(setup_pts)
            try:
                for cl in renamed:
                    xx, _ = gate.normalize_clause(cl, existing)
                    existing.add(xx)
            except gate.GateError:
                return None
            return renamed

        options = []
        for i in removed:
            if clause_points(clauses[i])[1] <= setup_pts and len(clause_points(clauses[i])[0]) == 1:
                options.append([i])
        if task["pairs"]:
            for i in removed:
                di, ri = clause_points(clauses[i])
                if len(di) != 1 or not ri <= setup_pts:
                    continue
                for j in removed:
                    dj, rj = clause_points(clauses[j])
                    if j != i and len(dj) == 1 and di[0] in rj and rj <= setup_pts | set(di):
                        options.append([i, j])
        found = 0
        for opt in options[: task["max_solutions"]]:
            aux = legal([clauses[i] for i in opt])
            if aux is None:
                continue
            try:
                g_s, _, t_s = saturate(engine, setup + [clauses[i] for i in opt], task["seed"], task["cpu_part"])
            except (engine._Timeout, Exception):  # noqa: BLE001
                continue
            if g_s is None:
                continue
            solved = []
            for name, args in open_facts:
                try:
                    if g_s.check(name, g_s.names2points(list(args))):
                        solved.append((name, args))
                except Exception:  # noqa: BLE001
                    continue
            if not solved:
                continue
            found += 1
            rng.shuffle(solved)
            for name, args in solved[: task["facts_per_solution"]]:
                rec["problems"].append({
                    "setup": "; ".join(setup), "goal": " ".join([name, *args]), "predicate": name,
                    "aux": aux, "aux_kinds": [kinds[i] for i in opt], "group": sorted(idx),
                    "t_setup": round(t_a, 3), "t_solution_saturation": round(t_s, 3),
                    "n_open": len(open_facts),
                })
            if len(opt) == 1 and found >= 2:
                break
    rec["status"] = "ok"
    return rec


def process_config_safe(task: dict) -> dict:
    try:
        return process_config(task)
    except BaseException as exc:  # noqa: BLE001 - one configuration must not stop generation
        rec = {k: task[k] for k in ("config_id", "kind", "split", "seed", "source", "source_id")}
        rec.update(status=f"crash:{type(exc).__name__}:{str(exc)[:200]}", problems=[])
        return rec


def load_public_bases(max_seconds: float, max_points: int) -> list[dict]:
    split_of = {}
    for split, paths in EXISTING.items():
        for path in paths:
            if path.exists():
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        split_of[json.loads(line)["source_id"]] = split
    bases = []
    for source, path in SCREENS:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("status") not in ("solved", "saturated"):
                continue
            if r["seconds"] > max_seconds or int(r.get("n_points") or 99) > max_points:
                continue
            bases.append({"source": source, "source_id": r["source_id"], "setup": r["setup"],
                          "seed": int(r["seed"]), "split": split_of.get(r["source_id"])})
    return bases


def make_tasks(args) -> list[dict]:
    common = {"cpu_full": args.cpu_full, "cpu_part": args.cpu_part, "max_groups": args.max_groups,
              "checks_per_group": args.checks_per_group, "max_solutions": args.max_solutions,
              "facts_per_solution": args.facts_per_solution, "pairs": True}
    tasks = []
    for b in load_public_bases(args.max_screen_seconds, args.max_points):
        cid = f"public:{b['source']}:{b['source_id']}"
        split = b["split"] or ("test" if stable_int(SALT, "split", cid) % 1000 < 660 else "train")
        tasks.append(dict(common, config_id=cid, kind="public", split=split, seed=b["seed"],
                          source=b["source"], source_id=b["source_id"], setup=b["setup"]))
    for i in range(args.random_configs):
        cid = f"random:{i:05d}"
        split = "test" if stable_int(SALT, "split", cid) % 1000 < 660 else "train"
        tasks.append(dict(common, config_id=cid, kind="random", split=split,
                          seed=stable_int(SALT, "seed", cid) % (2**31), source="random", source_id=cid))
    random.Random(stable_int(SALT, "task-order")).shuffle(tasks)
    # Interleave: one public base per `public_every` random configurations.
    pub = [t for t in tasks if t["kind"] == "public"]
    rnd = [t for t in tasks if t["kind"] == "random"]
    out = []
    while pub or rnd:
        for _ in range(args.public_every):
            if rnd:
                out.append(rnd.pop(0))
        if pub:
            out.append(pub.pop(0))
    return out


def cmd_generate(args) -> None:
    from evaluate import effective_cpus  # evaluator-owned helper

    done = set()
    if POOL.exists():
        for line in POOL.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["config_id"])
    tasks = [t for t in make_tasks(args) if t["config_id"] not in done]
    workers = args.workers or effective_cpus()
    n_prob = 0
    n_productive = 0
    if POOL.exists():
        for line in POOL.read_text(encoding="utf-8").splitlines():
            if line.strip() and json.loads(line)["problems"]:
                n_productive += 1
    print(f"[synth] {len(done)} configs done, {len(tasks)} to go, {workers} workers", file=sys.stderr, flush=True)
    started = time.time()
    ctx = mp.get_context("fork")
    with POOL.open("a", encoding="utf-8") as f, ctx.Pool(workers, maxtasksperchild=10) as pool:
        for rec in pool.imap_unordered(process_config_safe, tasks):
            f.write(json.dumps(rec, sort_keys=True) + "\n")
            f.flush()
            n_prob += len(rec["problems"])
            n_productive = n_productive + (1 if rec["problems"] else 0)
            print(f"[synth] {rec['config_id']} {rec['status']} t={rec.get('t_full')} facts={rec.get('n_facts')} "
                  f"groups={rec.get('n_groups')} problems={len(rec['problems'])} total={n_prob} "
                  f"({time.time() - started:.0f}s)", file=sys.stderr, flush=True)
            if time.time() - started > args.budget_seconds or n_productive >= args.stop_productive:
                print(f"[synth] stopping: productive={n_productive}", file=sys.stderr, flush=True)
                pool.terminate()
                break


# --------------------------------------------------------------------------
# select


def attempt_timeout(t_unsolved: float, t_solved: float) -> int:
    return int(min(12, max(4, math.ceil(3.0 * max(t_unsolved, t_solved) + 2.0))))


def verify_config(task: dict) -> dict:
    """Pick up to `per_config` verified problems of one configuration."""
    import engine  # noqa: E402

    out = {"config_id": task["config_id"], "problems": [], "checked": 0, "rejected": {}}
    used_groups: set = set()
    used_preds: set = set()
    cands = sorted(task["candidates"], key=lambda c: (tuple(c["group"]) in used_groups, c["_r"]))
    for cand in cands:
        if len(out["problems"]) >= task["per_config"]:
            break
        if tuple(cand["group"]) in used_groups or (cand["predicate"] in used_preds and len(cands) > 2):
            continue
        out["checked"] += 1
        st0, t0 = engine.verify(cand["setup"], cand["goal"], [], task["seed"], task["cpu_check"])
        if st0 != "saturated":
            out["rejected"][f"alone:{st0}"] = out["rejected"].get(f"alone:{st0}", 0) + 1
            continue
        st1, t1 = engine.verify(cand["setup"], cand["goal"], cand["aux"], task["seed"], task["cpu_check"])
        if st1 != "solved":
            out["rejected"][f"aux:{st1}"] = out["rejected"].get(f"aux:{st1}", 0) + 1
            continue
        coords = engine.draw_coordinates(cand["setup"], cand["goal"], task["seed"])
        if coords is None:
            out["rejected"]["draw"] = out["rejected"].get("draw", 0) + 1
            continue
        used_groups.add(tuple(cand["group"]))
        used_preds.add(cand["predicate"])
        out["problems"].append(dict(cand, t_alone=round(t0, 3), t_solution=round(t1, 3), coords=coords,
                                    timeout=attempt_timeout(max(t0, cand["t_solution_saturation"]), t1)))
    return out


def cmd_select(args) -> None:
    from evaluate import effective_cpus  # evaluator-owned helper

    recs = [json.loads(l) for l in POOL.read_text(encoding="utf-8").splitlines() if l.strip()]
    by_id = {}
    tasks = []
    for rec in recs:
        if rec.get("status") != "ok" or not rec["problems"]:
            continue
        rng = random.Random(stable_int(SALT, "select", rec["config_id"]))
        cands = []
        for c in rec["problems"]:
            if c["t_solution_saturation"] > args.max_solution_seconds or c["t_setup"] > args.max_solution_seconds:
                continue
            cands.append(dict(c, _r=rng.random()))
        if not cands:
            continue
        by_id[rec["config_id"]] = rec
        tasks.append({"config_id": rec["config_id"], "seed": int(rec["seed"]), "candidates": cands,
                      "per_config": args.per_config_public if rec["kind"] == "public" else args.per_config,
                      "cpu_check": args.cpu_check})
    workers = args.workers or effective_cpus()
    print(f"[select] {len(tasks)} productive configurations, {workers} workers", file=sys.stderr, flush=True)
    results = []
    ctx = mp.get_context("fork")
    with ctx.Pool(workers, maxtasksperchild=10) as pool:
        for res in pool.imap_unordered(verify_config, tasks):
            results.append(res)
            print(f"[select] {res['config_id']} kept={len(res['problems'])} checked={res['checked']} "
                  f"rejected={res['rejected']}", file=sys.stderr, flush=True)
    results.sort(key=lambda r: r["config_id"])

    rows = {"test": [], "train": []}
    for res in results:
        rec = by_id[res["config_id"]]
        for prob in res["problems"]:
            rows[rec["split"]].append((rec, prob))
    caps = {"test": args.max_test, "train": args.max_train}
    summary = {}
    for split, items in rows.items():
        rng = random.Random(stable_int(SALT, "order", split))
        rng.shuffle(items)
        if len(items) > caps[split]:
            seen, first, rest = set(), [], []
            for rec, prob in items:
                (rest if rec["config_id"] in seen else first).append((rec, prob))
                seen.add(rec["config_id"])
            items = (first + rest)[: caps[split]]
        items.sort(key=lambda rp: (rp[0]["config_id"], rp[1]["goal"]))
        prefix = "stest" if split == "test" else "strain"
        out_rows, sol_rows = [], []
        for idx, (rec, prob) in enumerate(items, start=1):
            pid = f"{prefix}_{idx:03d}"
            row = {
                "problem_id": pid,
                "config": rec["kind"],
                "source_id": rec["source_id"],
                "difficulty": None,
                "setup": prob["setup"],
                "goal": prob["goal"],
                "seed": int(rec["seed"]),
                "timeout": prob["timeout"],
                "ddar_alone_seconds": prob["t_alone"],
                "coords": prob["coords"],
            }
            sol = {"problem_id": pid, "aux": prob["aux"], "kinds": prob["aux_kinds"], "config": rec["kind"],
                   "predicate": prob["predicate"], "t_solution": prob["t_solution"]}
            if split == "train":
                row["known_aux"] = prob["aux"]
            out_rows.append(row)
            sol_rows.append(sol)
        path = TEST_OUT if split == "test" else TRAIN_OUT
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in out_rows), encoding="utf-8")
        if split == "test":
            SOLUTIONS_OUT.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in sol_rows),
                                     encoding="utf-8")

        def count(key):
            c = {}
            for s in sol_rows:
                k = key(s)
                c[k] = c.get(k, 0) + 1
            return dict(sorted(c.items(), key=lambda kv: -kv[1]))

        summary[split] = {
            "problems": len(out_rows), "configurations": len({r["source_id"] for r in out_rows}),
            "config_kind": count(lambda s: s["config"]),
            "aux_kinds": count(lambda s: "+".join(s["kinds"])),
            "aux_count": count(lambda s: len(s["kinds"])),
            "predicates": count(lambda s: s["predicate"]),
            "timeout_sum": sum(r["timeout"] for r in out_rows),
            "alone_seconds_sum": round(sum(r["ddar_alone_seconds"] for r in out_rows), 1),
            "points_mean": round(sum(len(r["coords"]) for r in out_rows) / max(1, len(out_rows)), 2),
        }
    print(json.dumps(summary, indent=1))
    SUMMARY_OUT.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--random-configs", type=int, default=4000)
    g.add_argument("--public-every", type=int, default=3)
    g.add_argument("--max-screen-seconds", type=float, default=2.0)
    g.add_argument("--max-points", type=int, default=11)
    g.add_argument("--cpu-full", type=float, default=6.0)
    g.add_argument("--cpu-part", type=float, default=4.0)
    g.add_argument("--max-groups", type=int, default=5)
    g.add_argument("--checks-per-group", type=int, default=150)
    g.add_argument("--max-solutions", type=int, default=4)
    g.add_argument("--facts-per-solution", type=int, default=3)
    g.add_argument("--budget-seconds", type=float, default=3000)
    g.add_argument("--stop-productive", type=int, default=480)
    g.add_argument("--workers", type=int, default=0)
    g.set_defaults(func=cmd_generate)
    s = sub.add_parser("select")
    s.add_argument("--per-config", type=int, default=2)
    s.add_argument("--per-config-public", type=int, default=2)
    s.add_argument("--max-solution-seconds", type=float, default=2.5)
    s.add_argument("--cpu-check", type=float, default=20.0)
    s.add_argument("--max-test", type=int, default=240)
    s.add_argument("--max-train", type=int, default=120)
    s.add_argument("--workers", type=int, default=0)
    s.set_defaults(func=cmd_select)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
