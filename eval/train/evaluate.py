#!/usr/bin/env python3
"""Visible train evaluation: run every proposer on train problems, verify with DDAR.

The train problems (premises, goals, seeds, per-problem timeouts) are the
visible file ``data/benchmarks/hageo409_train.jsonl``; the protocol is the same
as the held-out test evaluation.  For every executable ``proposers/<name>.sh`` on disk the
evaluator

1. writes the goal-free problem setups plus a numerical drawing to a private
   temporary file and runs the proposer on it under a time limit,
2. checks the returned auxiliary constructions against the validity gate
   (``gate.py``) and the evaluator's attempt budget,
3. runs its own DDAR engine on premises + each attempt, in order, until the
   goal is proved or the attempts run out,
4. computes every scored number from those verification results.

A proposer that crashes, times out, writes malformed output or breaks a gate
rule is scored as a failed run: the worst value in every metric.  The fixed
baselines (DDAR alone, random auxiliary constructions) are evaluator-owned
results stored in ``baselines.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import gate  # noqa: E402

SLICE = "train"
PROBLEMS = ROOT / "data" / "benchmarks" / "hageo409_train.jsonl"
CONFIG = HERE / "config.json"
BASELINES = HERE / "baselines.json"
PROPOSER_DIR = ROOT / "proposers"
DEFAULT_OUT = ROOT / "scoring" / "scores_train.json"
DETAILS_OUT = ROOT / "outputs" / "eval_train_details.json"
FIXED_BASELINES = ("ddar", "random_aux")


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def worst_metrics(config: dict) -> dict:
    return {m: float(v) for m, v in config["worst"].items()}


def compute_metrics(first_success: dict, problems: list[dict], config: dict) -> dict:
    k_max = int(config["max_attempts"])
    thr = config.get("upper_half_threshold")
    if thr is None:
        diffs = sorted(float(p["difficulty"]) for p in problems)
        thr = diffs[len(diffs) // 2]
    thr = float(thr)
    n = len(problems)
    solved = [p for p in problems if first_success.get(p["problem_id"]) is not None]
    upper = [p for p in problems if float(p["difficulty"]) >= thr]
    auc = sum((k_max - int(first_success[p["problem_id"]]) + 1) / k_max for p in solved)
    return {
        "solve_rate": len(solved) / n,
        "upper_half_solve_rate": (
            sum(1 for p in upper if first_success.get(p["problem_id"]) is not None) / len(upper)
        ),
        "pass_auc": auc / n,
    }


# --------------------------------------------------------------------------
# verification (may run in worker processes)


class Cache:
    def __init__(self, path: Path | None):
        self.path = path
        self.data: dict[str, list] = {}
        if path is not None and path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    key, value = json.loads(line)
                    self.data[key] = value

    @staticmethod
    def key(problem: dict, aux: list[str]) -> str:
        blob = json.dumps(
            [problem["setup"], problem["goal"], aux, int(problem["seed"]), float(problem["timeout"])]
        )
        return hashlib.sha256(blob.encode()).hexdigest()

    def add(self, key: str, value: list) -> None:
        self.data[key] = value
        if self.path is not None:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps([key, value]) + "\n")


_CACHE: Cache | None = None


def _verify_problem(task):
    problem, attempts = task
    import engine  # noqa: E402  (evaluator-owned)

    log = []
    memo = {}
    for index, aux in enumerate(attempts, start=1):
        key = Cache.key(problem, aux)
        if key in memo:
            status, seconds = memo[key], 0.0
        elif _CACHE is not None and key in _CACHE.data:
            status, seconds = _CACHE.data[key]
        else:
            status, seconds = engine.verify(
                problem["setup"], problem["goal"], aux, int(problem["seed"]), float(problem["timeout"])
            )
            log.append((key, [status, seconds]))
        memo[key] = status
        if status == "solved":
            return problem["problem_id"], index, index, log
    return problem["problem_id"], None, len(attempts), log


def verify_all(problems: list[dict], attempts_by_id: dict, workers: int) -> tuple[dict, dict]:
    tasks = [(p, attempts_by_id.get(p["problem_id"], [])) for p in problems]
    first_success: dict = {}
    attempts_used: dict = {}

    def consume(result):
        pid, first, used, log = result
        first_success[pid] = first
        attempts_used[pid] = used
        if _CACHE is not None:
            for key, value in log:
                _CACHE.add(key, value)

    if workers <= 1:
        for task in tasks:
            consume(_verify_problem(task))
    else:
        ctx = mp.get_context("fork")
        with ctx.Pool(workers, maxtasksperchild=4) as pool:
            for result in pool.imap_unordered(_verify_problem, tasks):
                consume(result)
    return first_success, attempts_used


# --------------------------------------------------------------------------
# proposers


def proposer_input(problems: list[dict], coords: dict, config: dict) -> list[dict]:
    rows = []
    for p in problems:
        rows.append(
            {
                "problem_id": p["problem_id"],
                "setup": p["setup"],
                "points": gate.setup_point_names(p["setup"]),
                "coords": coords.get(p["problem_id"]),
                "difficulty": p["difficulty"],
                "max_attempts": int(config["max_attempts"]),
                "max_aux_per_attempt": int(config["max_aux_per_attempt"]),
            }
        )
    return rows


def run_proposer(script: Path, rows: list[dict], config: dict, workdir: Path) -> tuple[list | None, str]:
    in_path = workdir / "problems.jsonl"
    out_path = workdir / "proposals.jsonl"
    log_path = workdir / "proposer.log"
    with in_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    if out_path.exists():
        out_path.unlink()
    limit = max(float(config["proposer_min_seconds"]), float(config["proposer_seconds_per_problem"]) * len(rows))
    started = time.time()
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            ["bash", str(script), str(in_path), str(out_path)],
            cwd=str(ROOT),
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            code = proc.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            return None, f"proposer exceeded its time limit of {limit:.0f}s"
    elapsed = time.time() - started
    if code != 0:
        return None, f"proposer exited with status {code}"
    if not out_path.exists():
        return None, "proposer wrote no output file"
    rows_out = []
    try:
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows_out.append(json.loads(line))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, f"malformed output: {exc}"
    return rows_out, f"ok ({elapsed:.0f}s)"


def discover_proposers(only: list[str] | None) -> dict[str, Path]:
    found = {}
    if PROPOSER_DIR.is_dir():
        for path in sorted(PROPOSER_DIR.glob("*.sh")):
            name = path.stem
            if name in FIXED_BASELINES:
                name = f"proposer_{name}"
            found[name] = path
    if only:
        found = {k: v for k, v in found.items() if k in only}
    return found


def evaluate_proposer(name, script, problems, coords, config, workers, details):
    rows = proposer_input(problems, coords, config)
    workdir = Path(tempfile.mkdtemp(prefix=f"hageo_eval_{SLICE}_"))
    try:
        output, message = run_proposer(script, rows, config, workdir)
        log_tail = ""
        log_file = workdir / "proposer.log"
        if log_file.exists():
            log_tail = log_file.read_text(encoding="utf-8", errors="replace")[-2000:]
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    if output is None:
        details[name] = {"status": f"failed: {message}", "log_tail": log_tail}
        return worst_metrics(config)
    try:
        attempts = gate.validate_rows(
            output, problems, int(config["max_attempts"]), int(config["max_aux_per_attempt"])
        )
    except gate.GateError as exc:
        details[name] = {"status": f"failed: gate violation: {exc}"}
        return worst_metrics(config)
    started = time.time()
    first, used = verify_all(problems, attempts, workers)
    metrics = compute_metrics(first, problems, config)
    details[name] = {
        "status": "ok",
        "proposer": message,
        "verify_seconds": round(time.time() - started, 1),
        "first_success": first,
        "attempts_verified": used,
        "attempts_submitted": {pid: len(a) for pid, a in attempts.items()},
    }
    return metrics


def recompute_baselines(problems, coords, config, workers) -> dict:
    out = {"_config": {k: config[k] for k in ("max_attempts", "max_aux_per_attempt")}}
    # DDAR alone: verify each problem with no auxiliary construction.
    first, _ = verify_all(problems, {p["problem_id"]: [[]] for p in problems}, workers)
    out["ddar"] = {pid: (None if v is None else 1) for pid, v in first.items()}
    for name, rel in config["baseline_proposers"].items():
        details: dict = {}
        evaluate_proposer(name, ROOT / rel, problems, coords, config, workers, details)
        if details[name]["status"] != "ok":
            raise RuntimeError(f"baseline {name} failed: {details[name]}")
        out[name] = details[name]["first_success"]
    return out


def main() -> None:
    global _CACHE
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--details", type=Path, default=DETAILS_OUT)
    parser.add_argument("--only", nargs="*", default=None, help="audit use: score only these proposers")
    parser.add_argument("--cache", type=Path, default=None, help="audit use: verification cache file")
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--recompute-baselines", action="store_true")
    parser.add_argument("--problems", type=Path, default=PROBLEMS, help="audit use: alternative problem file")
    parser.add_argument("--baselines", type=Path, default=BASELINES, help="audit use: alternative baseline file")
    args = parser.parse_args()

    config = load_config()
    problems = read_jsonl(args.problems)
    baselines_path = args.baselines
    workers = args.workers or max(1, len(os.sched_getaffinity(0)))
    if args.cache is not None:
        args.cache.parent.mkdir(parents=True, exist_ok=True)
        _CACHE = Cache(args.cache)

    import engine  # noqa: E402

    coords = {}
    for p in problems:
        coords[p["problem_id"]] = engine.draw_coordinates(p["setup"], p["goal"], int(p["seed"]))

    if args.recompute_baselines:
        baselines_path.write_text(
            json.dumps(recompute_baselines(problems, coords, config, workers), indent=1, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )

    results: dict = {}
    details: dict = {}
    baselines = json.loads(baselines_path.read_text(encoding="utf-8")) if baselines_path.exists() else {}
    for name in FIXED_BASELINES:
        if name in baselines:
            results[name] = compute_metrics(baselines[name], problems, config)
            details[name] = {"status": "ok (fixed evaluator baseline)"}

    for name, script in discover_proposers(args.only).items():
        print(f"[eval:{SLICE}] proposer {name}", file=sys.stderr, flush=True)
        try:
            results[name] = evaluate_proposer(name, script, problems, coords, config, workers, details)
        except Exception as exc:  # noqa: BLE001 - any failure scores as a failed run
            details[name] = {"status": f"failed: evaluator error {type(exc).__name__}: {exc}"}
            results[name] = worst_metrics(config)
        print(f"[eval:{SLICE}] {name}: {details[name]['status']} {results[name]}", file=sys.stderr, flush=True)

    exp = config["experiment"]
    scores = {
        "slice": SLICE,
        "experiments": {
            exp: {
                "results": results,
                "_status": {name: details[name]["status"] for name in results},
            }
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(scores, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.details.parent.mkdir(parents=True, exist_ok=True)
    args.details.write_text(json.dumps(details, indent=1, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
