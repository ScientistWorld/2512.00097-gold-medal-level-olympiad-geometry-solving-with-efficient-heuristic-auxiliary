#!/usr/bin/env python3
"""Derived auxiliary-construction problems on public olympiad configurations.

Evaluator-owned (held-out side).  Enlarges the test with many problems that
provably need an auxiliary point while keeping the answers private:

``generate``  For every *base* configuration -- the premises of a public
    HAGeo-409 or JGEX-231 problem whose DDAR closure is cheap -- run DDAR to
    saturation, then add a few random *hidden* points E, each defined the way
    olympiad statements define points (circumcentre, intersection of two
    lines, foot, midpoint, second intersection with a circle, ...; weights
    follow the construction frequencies of the two public benchmarks).  Every
    fact about the *original* points that DDAR derives with E but not without
    it is a candidate goal.  The draw of E uses a private salt, so neither the
    goals nor the needed constructions exist in any public file.

``select``  Per base keep a few (E, fact) pairs, re-check each with the
    evaluator's own verifier (premises alone: DDAR saturates without the goal;
    premises + E: DDAR proves it), fix the per-attempt CPU limit from the
    measured times, store the evaluator's drawing, and split by base
    configuration into the hidden test file and the visible train file.

The proposer sees only the original premises (identical to the public
statement, renamed) and a drawing; the goal and E stay here.
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

SALT = "hageo-gym-v3-derived-b82c92a5929afd33"
POOL = HERE / "derived_pool.jsonl"
TEST_OUT = HERE / "problems_derived.jsonl"
SOLUTIONS_OUT = HERE / "derived_solutions.jsonl"
TRAIN_OUT = ROOT / "data" / "benchmarks" / "derived_train.jsonl"
SCREENS = (("hageo409", HERE / "screening.jsonl"), ("jgex", HERE / "screening_jgex.jsonl"))
EXISTING = {
    "test": (HERE / "problems.jsonl", HERE / "problems_jgex.jsonl"),
    "train": (ROOT / "data" / "benchmarks" / "hageo409_train.jsonl",
              ROOT / "data" / "benchmarks" / "jgex231_train.jsonl"),
}
PREDICATES = ("coll", "cyclic", "para", "perp", "cong", "midp", "eqangle", "eqratio")
HIDDEN_NAMES = ("zz1", "zz2")

# Point definitions used for the hidden points, weighted by how often olympiad
# statements in HAGeo-409 / JGEX-231 define points this way (gate-legal forms).
VOCAB = (
    ("circumcenter", 14), ("line_line", 13), ("foot", 12), ("midpoint", 10), ("line_circle", 10),
    ("circle_circle", 4), ("incenter", 4), ("tline_line", 4), ("orthocenter", 3), ("reflect", 3),
    ("pline_line", 3), ("mirror", 2), ("bisector_line", 2), ("bline_line", 2), ("tline_tline", 2),
    ("excenter", 1),
)


def stable_int(*parts) -> int:
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16)


def setup_names(setup: str) -> list[str]:
    names: list[str] = []
    for clause in setup.split("; "):
        for n in clause.split(" = ", 1)[0].split():
            n = n.split("@", 1)[0]
            if n and n not in names:
                names.append(n)
    return names


def sample_clause(x: str, pts: list[str], rng: random.Random) -> tuple[str, str]:
    kinds, weights = zip(*VOCAB)
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
    else:  # pragma: no cover
        raise ValueError(kind)
    return kind, f"{x} = {body}"


# --------------------------------------------------------------------------
# generate


def _saturate(engine, statement: str, seed: int, cpu: float, max_tries: int = 60):
    """Draw and run DDAR to saturation (no goal).  Returns (graph, added, seconds) or raises."""
    A = engine.ag()
    started = time.process_time()
    with engine.hard_timeout(cpu):
        g, p = engine.bounded_build(statement, seed, max_tries=max_tries)
        if g is None:
            return None, [], time.process_time() - started
        _, _, _, _, added = A["ddar"].solve(g, A["rules"], p, max_level=1000, timeout=100000)
    return g, added, time.process_time() - started


def process_base(task: dict) -> dict:
    import engine  # noqa: E402

    A = engine.ag()
    nm = A["nm"]
    base = dict(task["base"])
    setup, seed = base["setup"], int(base["seed"])
    names = setup_names(setup)
    name_set = set(names)
    rec = {k: base[k] for k in ("base_id", "source", "source_id", "split", "setup", "seed", "difficulty")}
    public = base.get("public_goal", "").split()
    public_key = (public[0], tuple(sorted(public[1:]))) if public else None
    rec["samples"] = []
    try:
        g_s, _, t_s = _saturate(engine, setup, seed, task["cpu_base"])
    except engine._Timeout:
        rec.update(status="timeout_base")
        return rec
    except Exception as exc:  # noqa: BLE001
        rec.update(status=f"error_base:{type(exc).__name__}")
        return rec
    if g_s is None:
        rec.update(status="unbuildable_base")
        return rec
    rec.update(status="ok", t_base=round(t_s, 3))
    rng = random.Random(stable_int(SALT, "hidden", base["base_id"]))
    for j in range(task["samples"]):
        n_hidden = 1 if rng.random() < task["p_single"] else 2
        pts = list(names)
        clauses, kinds = [], []
        for k in range(n_hidden):
            for _ in range(20):
                try:
                    kind, clause = sample_clause(HIDDEN_NAMES[k], pts, rng)
                    break
                except ValueError:  # too few points for this construction
                    continue
            else:
                break
            kinds.append(kind)
            clauses.append(clause)
            pts.append(HIDDEN_NAMES[k])
        if not clauses:
            continue
        sample = {"clauses": clauses, "kinds": kinds}
        try:
            g, added, t_se = _saturate(engine, setup + "; " + "; ".join(clauses), seed, task["cpu_hidden"],
                                       max_tries=25)
        except engine._Timeout:
            sample["status"] = "timeout"
            rec["samples"].append(sample)
            continue
        except Exception as exc:  # noqa: BLE001
            sample["status"] = f"error:{type(exc).__name__}"
            rec["samples"].append(sample)
            continue
        if g is None:
            sample["status"] = "unbuildable"
            rec["samples"].append(sample)
            continue
        facts = {}
        for dep in added:
            if dep.name not in PREDICATES:
                continue
            arg_names = [getattr(a, "name", None) for a in dep.args]
            if any(n not in name_set for n in arg_names):
                continue
            facts.setdefault((dep.name, tuple(arg_names)), None)
        # Facts about the original points that the premises alone do not give.
        # Checked in a random order per predicate, a bounded number each.
        frng = random.Random(stable_int(SALT, "facts", base["base_id"], j))
        by_pred: dict = {}
        for name, arg_names in sorted(facts):
            if public_key == (name, tuple(sorted(arg_names))):
                continue  # the public problem's own goal is not a new problem
            by_pred.setdefault(name, []).append(list(arg_names))
        kept, checked = {}, {}
        try:
            with engine.hard_timeout(task["cpu_hidden"]):
                for name in sorted(by_pred):
                    items = by_pred[name]
                    frng.shuffle(items)
                    for arg_names in items[: task["checks_per_predicate"]]:
                        checked[name] = checked.get(name, 0) + 1
                        try:
                            pts_s = g_s.names2points(list(arg_names))
                            if g_s.check(name, pts_s) or not nm.check(name, pts_s):
                                continue
                        except Exception:  # noqa: BLE001
                            continue
                        kept.setdefault(name, []).append(arg_names)
                        if len(kept[name]) >= task["facts_per_predicate"]:
                            break
        except engine._Timeout:
            sample["fact_check_timeout"] = True
        sample.update(status="ok", t_hidden=round(t_se, 3), n_facts={k: len(v) for k, v in by_pred.items()},
                      n_checked=checked, facts=kept)
        rec["samples"].append(sample)
    return rec


def load_bases(max_seconds: float, max_points: int) -> list[dict]:
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
            sid = r["source_id"]
            split = split_of.get(sid)
            if split is None:
                split = "test" if (stable_int(SALT, "split", source, sid) % 1000) < 620 else "train"
            bases.append({
                "base_id": f"{source}:{sid}",
                "source": source,
                "source_id": sid,
                "split": split,
                "setup": r["setup"],
                "seed": int(r["seed"]),
                "difficulty": r.get("difficulty"),
                "public_goal": r["goal"],
                "screen_seconds": r["seconds"],
            })
    bases.sort(key=lambda b: (b["screen_seconds"], b["base_id"]))
    return bases


def cmd_generate(args) -> None:
    from evaluate import effective_cpus  # evaluator-owned helper

    done = set()
    if POOL.exists():
        for line in POOL.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["base_id"])
    bases = [b for b in load_bases(args.max_screen_seconds, args.max_points) if b["base_id"] not in done]
    workers = args.workers or effective_cpus()
    print(f"[derive] {len(done)} bases done, {len(bases)} to go, {workers} workers", file=sys.stderr, flush=True)
    tasks = [{"base": b, "samples": args.samples, "p_single": args.p_single, "cpu_base": args.cpu_base,
              "cpu_hidden": args.cpu_hidden, "facts_per_predicate": args.facts_per_predicate,
              "checks_per_predicate": args.checks_per_predicate} for b in bases]
    started = time.time()
    ctx = mp.get_context("fork")
    with POOL.open("a", encoding="utf-8") as f, ctx.Pool(workers, maxtasksperchild=8) as pool:
        for rec in pool.imap_unordered(process_base, tasks):
            f.write(json.dumps(rec, sort_keys=True) + "\n")
            f.flush()
            n_ok = sum(1 for s in rec["samples"] if s.get("status") == "ok" and s.get("facts"))
            print(f"[derive] {rec['base_id']} {rec['status']} t={rec.get('t_base')} productive={n_ok}/"
                  f"{len(rec['samples'])} ({time.time() - started:.0f}s)", file=sys.stderr, flush=True)
            if time.time() - started > args.budget_seconds:
                print("[derive] time budget reached", file=sys.stderr, flush=True)
                pool.terminate()
                break


# --------------------------------------------------------------------------
# select


def attempt_timeout(t_unsolved: float, t_solved: float) -> int:
    return int(min(12, max(4, math.ceil(3.0 * max(t_unsolved, t_solved) + 2.0))))


def verify_base(task: dict) -> dict:
    """Pick up to `per_base` verified problems from one base's candidate list."""
    import engine  # noqa: E402

    out = {"base_id": task["base_id"], "problems": [], "checked": 0, "rejected": {}}
    used_kinds: set = set()
    for cand in task["candidates"]:
        if len(out["problems"]) >= task["per_base"]:
            break
        if task["distinct_kinds"] and cand["kinds"][0] in used_kinds:
            continue
        out["checked"] += 1
        st0, t0 = engine.verify(task["setup"], cand["goal"], [], task["seed"], task["cpu_check"])
        if st0 != "saturated":
            out["rejected"][f"alone:{st0}"] = out["rejected"].get(f"alone:{st0}", 0) + 1
            continue
        st1, t1 = engine.verify(task["setup"], cand["goal"], cand["clauses"], task["seed"], task["cpu_check"])
        if st1 != "solved":
            out["rejected"][f"hidden:{st1}"] = out["rejected"].get(f"hidden:{st1}", 0) + 1
            continue
        coords = engine.draw_coordinates(task["setup"], cand["goal"], task["seed"])
        if coords is None:
            out["rejected"]["draw"] = out["rejected"].get("draw", 0) + 1
            continue
        used_kinds.add(cand["kinds"][0])
        out["problems"].append(dict(cand, t_alone=round(t0, 3), t_solution=round(t1, 3), coords=coords,
                                    timeout=attempt_timeout(max(t0, cand["t_hidden"]), t1)))
    return out


def cmd_select(args) -> None:
    from evaluate import effective_cpus  # evaluator-owned helper

    recs = [json.loads(l) for l in POOL.read_text(encoding="utf-8").splitlines() if l.strip()]
    tasks = []
    for rec in recs:
        if rec.get("status") != "ok":
            continue
        rng = random.Random(stable_int(SALT, "select", rec["base_id"]))
        cands = []
        for j, s in enumerate(rec["samples"]):
            if s.get("status") != "ok" or not s.get("facts"):
                continue
            if s["t_hidden"] > args.max_hidden_seconds:
                continue
            preds = sorted(s["facts"])
            pred = rng.choice(preds)
            args_ = rng.choice(s["facts"][pred])
            cands.append({"sample": j, "clauses": s["clauses"], "kinds": s["kinds"], "t_hidden": s["t_hidden"],
                          "goal": " ".join([pred] + list(args_)), "predicate": pred})
        if cands:
            tasks.append({"base_id": rec["base_id"], "setup": rec["setup"], "seed": int(rec["seed"]),
                          "candidates": cands, "per_base": args.per_base, "distinct_kinds": True,
                          "cpu_check": args.cpu_check, "_rec": rec})
    by_id = {t["base_id"]: t.pop("_rec") for t in tasks}
    workers = args.workers or effective_cpus()
    print(f"[select] {len(tasks)} productive bases, {workers} workers", file=sys.stderr, flush=True)
    results = []
    ctx = mp.get_context("fork")
    with ctx.Pool(workers, maxtasksperchild=8) as pool:
        for res in pool.imap_unordered(verify_base, tasks):
            results.append(res)
            print(f"[select] {res['base_id']} kept={len(res['problems'])} checked={res['checked']} "
                  f"rejected={res['rejected']}", file=sys.stderr, flush=True)
    results.sort(key=lambda r: r["base_id"])

    rows = {"test": [], "train": []}
    for res in results:
        rec = by_id[res["base_id"]]
        for prob in res["problems"]:
            rows[rec["split"]].append((rec, prob))
    caps = {"test": args.max_test, "train": args.max_train}
    summary = {}
    for split, items in rows.items():
        rng = random.Random(stable_int(SALT, "order", split))
        rng.shuffle(items)
        if len(items) > caps[split]:
            # Drop whole problems, at most one per base first, to keep many bases.
            seen, first, rest = set(), [], []
            for rec, prob in items:
                (rest if rec["base_id"] in seen else first).append((rec, prob))
                seen.add(rec["base_id"])
            items = (first + rest)[: caps[split]]
        items.sort(key=lambda rp: (rp[0]["base_id"], rp[1]["sample"]))
        prefix = "dtest" if split == "test" else "dtrain"
        out_rows, sol_rows = [], []
        for idx, (rec, prob) in enumerate(items, start=1):
            pid = f"{prefix}_{idx:03d}"
            row = {
                "problem_id": pid,
                "source_id": rec["source_id"],
                "base": rec["source"],
                "difficulty": None,
                "setup": rec["setup"],
                "goal": prob["goal"],
                "seed": int(rec["seed"]),
                "timeout": prob["timeout"],
                "ddar_alone_seconds": prob["t_alone"],
                "coords": prob["coords"],
            }
            sol = {"problem_id": pid, "aux": prob["clauses"], "kinds": prob["kinds"],
                   "predicate": prob["predicate"], "t_solution": prob["t_solution"]}
            if split == "train":
                row["known_aux"] = prob["clauses"]
            out_rows.append(row)
            sol_rows.append(sol)
        path = TEST_OUT if split == "test" else TRAIN_OUT
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in out_rows), encoding="utf-8")
        if split == "test":
            SOLUTIONS_OUT.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in sol_rows),
                                     encoding="utf-8")
        kinds, preds = {}, {}
        for s in sol_rows:
            kinds[s["kinds"][0] + ("+1" if len(s["kinds"]) > 1 else "")] = kinds.get(
                s["kinds"][0] + ("+1" if len(s["kinds"]) > 1 else ""), 0) + 1
            preds[s["predicate"]] = preds.get(s["predicate"], 0) + 1
        summary[split] = {
            "problems": len(out_rows), "bases": len({r["source_id"] for r in out_rows}),
            "kinds": dict(sorted(kinds.items(), key=lambda kv: -kv[1])),
            "predicates": dict(sorted(preds.items(), key=lambda kv: -kv[1])),
            "timeout_sum": sum(r["timeout"] for r in out_rows),
            "alone_seconds_sum": round(sum(r["ddar_alone_seconds"] for r in out_rows), 1),
        }
    print(json.dumps(summary, indent=1))
    (HERE / "derived_summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--max-screen-seconds", type=float, default=2.5)
    g.add_argument("--max-points", type=int, default=11)
    g.add_argument("--samples", type=int, default=8)
    g.add_argument("--p-single", type=float, default=0.75)
    g.add_argument("--cpu-base", type=float, default=4.0)
    g.add_argument("--cpu-hidden", type=float, default=8.0)
    g.add_argument("--facts-per-predicate", type=int, default=6)
    g.add_argument("--checks-per-predicate", type=int, default=200)
    g.add_argument("--budget-seconds", type=float, default=3600)
    g.add_argument("--workers", type=int, default=0)
    g.set_defaults(func=cmd_generate)
    s = sub.add_parser("select")
    s.add_argument("--per-base", type=int, default=2)
    s.add_argument("--max-hidden-seconds", type=float, default=3.0)
    s.add_argument("--cpu-check", type=float, default=20.0)
    s.add_argument("--max-test", type=int, default=260)
    s.add_argument("--max-train", type=int, default=140)
    s.add_argument("--workers", type=int, default=0)
    s.set_defaults(func=cmd_select)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
