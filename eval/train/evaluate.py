#!/usr/bin/env python3
"""Visible train evaluation: run every proposer on train problems, verify with DDAR.

The train problems (premises, goals, seeds, per-problem timeouts) are the
visible files under ``data/benchmarks/``; the protocol is identical to the
held-out test evaluation.  For every executable ``proposers/<name>.sh`` on disk and every
experiment in ``config.json`` the evaluator

1. writes the goal-free problem setups plus a numerical drawing to a private
   temporary file and runs the proposer on it under a CPU-time limit (summed
   over the proposer's whole process tree),
2. checks the returned auxiliary constructions against the validity gate
   (``gate.py``) and the evaluator's attempt budget,
3. runs its own DDAR engine on premises + each attempt, in order, until the
   goal is proved or the attempts run out,
4. computes every scored number from those verification results.

A proposer that crashes, times out, writes malformed output or breaks a gate
rule is scored as a failed run: the worst value in every metric of every
experiment.  The fixed baselines (DDAR alone, random auxiliary constructions)
are evaluator-owned results stored next to each problem file.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import multiprocessing as mp
import os
import resource
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
CONFIG = HERE / "config.json"
PROPOSER_DIR = ROOT / "proposers"
DEFAULT_OUT = ROOT / "scoring" / "scores_train.json"
DETAILS_OUT = ROOT / "outputs" / "eval_train_details.json"
FIXED_BASELINES = ("ddar", "random_aux")


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def resolve(rel: str) -> Path:
    path = Path(rel)
    return path if path.is_absolute() else ROOT / path


def worst_metrics(exp: dict) -> dict:
    return {m: 0.0 for m in exp["metrics"]}


def compute_metrics(first_success: dict, problems: list[dict], exp: dict) -> dict:
    k_max = int(exp["max_attempts"])
    n = len(problems)
    solved = [p for p in problems if first_success.get(p["problem_id"]) is not None]
    out = {
        "solve_rate": len(solved) / n,
        "pass_auc": sum((k_max - int(first_success[p["problem_id"]]) + 1) / k_max for p in solved) / n,
    }
    if "hard_solve_rate" in exp["metrics"]:
        thr = float(exp["hard_difficulty_threshold"])
        hard = [p for p in problems if float(p["difficulty"]) >= thr]
        out["hard_solve_rate"] = sum(1 for p in hard if first_success.get(p["problem_id"]) is not None) / len(hard)
    return {m: out[m] for m in exp["metrics"]}


def _busy(n: int) -> float:
    t = time.perf_counter()
    acc = 0
    for i in range(n):
        acc += i * i
    return time.perf_counter() - t


def effective_cpus() -> int:
    """CPUs that really run in parallel (affinity mask, cgroup quota, probe).

    Verification timeouts are wall-clock limits, so workers must never
    outnumber the cores actually available.
    """
    try:
        n = len(os.sched_getaffinity(0))
    except AttributeError:
        n = os.cpu_count() or 1
    n = min(n, 32)
    for quota_file, period_file in (
        ("/sys/fs/cgroup/cpu.max", None),
        ("/sys/fs/cgroup/cpu/cpu.cfs_quota_us", "/sys/fs/cgroup/cpu/cpu.cfs_period_us"),
    ):
        try:
            if period_file is None:
                quota, period = Path(quota_file).read_text().split()[:2]
            else:
                quota, period = Path(quota_file).read_text().strip(), Path(period_file).read_text().strip()
            if quota not in ("max", "-1"):
                n = min(n, max(1, int(float(quota) / float(period))))
        except (OSError, ValueError):
            pass
    if n <= 1:
        return 1
    work = 3_000_000
    single = min(_busy(work), _busy(work))
    ctx = mp.get_context("fork")
    started = time.perf_counter()
    with ctx.Pool(n) as pool:
        pool.map(_busy, [work] * n)
    wall = time.perf_counter() - started
    return max(1, min(n, int(n * single / max(wall, 1e-9) + 0.3)))


# --------------------------------------------------------------------------
# verification (may run in worker processes)


class Cache:
    """Audit-only memo of verification results and proposer outputs."""

    def __init__(self, path: Path | None):
        self.path = path
        self.data: dict[str, list] = {}
        if path is not None and path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        key, value = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        continue
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

    def proposal_dir(self) -> Path | None:
        if self.path is None:
            return None
        d = self.path.parent / (self.path.stem + "_proposals")
        d.mkdir(parents=True, exist_ok=True)
        return d


_CACHE: Cache | None = None


def in_time(status: str, seconds: float, timeout: float) -> str:
    """A proof only counts if DDAR finished inside the attempt's CPU-time limit."""
    if status == "solved" and seconds > timeout + 1.0:
        return "timeout"
    return status


def _verify_problem(task):
    problem, attempts = task
    import engine  # noqa: E402  (evaluator-owned)

    log = []
    memo = {}
    for index, aux in enumerate(attempts, start=1):
        key = Cache.key(problem, aux)
        if key in memo:
            status = memo[key]
        elif _CACHE is not None and key in _CACHE.data:
            status = in_time(*_CACHE.data[key][:2], float(problem["timeout"]))
        else:
            status, seconds = engine.verify(
                problem["setup"], problem["goal"], aux, int(problem["seed"]), float(problem["timeout"])
            )
            log.append((key, [status, seconds]))
            status = in_time(status, seconds, float(problem["timeout"]))
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


def proposer_input(problems: list[dict], coords: dict, exp: dict, config: dict) -> list[dict]:
    rows = []
    for p in problems:
        rows.append(
            {
                "problem_id": p["problem_id"],
                "setup": p["setup"],
                "points": gate.setup_point_names(p["setup"]),
                "coords": coords.get(p["problem_id"]),
                "difficulty": p.get("difficulty"),
                "max_attempts": int(exp["max_attempts"]),
                "max_aux_per_attempt": int(exp["max_aux_per_attempt"]),
                "cpu_seconds_per_problem": float(config["proposer_cpu_seconds_per_problem"]),
            }
        )
    return rows


def _children_cpu() -> float:
    ru = resource.getrusage(resource.RUSAGE_CHILDREN)
    return ru.ru_utime + ru.ru_stime


def proposer_cpu_limit(config: dict, n_rows: int) -> float:
    return max(float(config["proposer_cpu_min_seconds"]), float(config["proposer_cpu_seconds_per_problem"]) * n_rows)


def _audit_fingerprint(script: Path, in_path: Path) -> str:
    h = hashlib.sha256(script.read_bytes() + in_path.read_bytes())
    for sub in ("method", "baseline", "redteam/hardening/proposers", "redteam/hardening2/proposers"):
        base = ROOT / sub
        if base.is_dir():
            for f in sorted(base.rglob("*.py")):
                h.update(str(f.relative_to(ROOT)).encode() + f.read_bytes())
    return h.hexdigest()


def run_proposer(script: Path, rows: list[dict], config: dict, workdir: Path) -> tuple[list | None, str]:
    in_path = workdir / "problems.jsonl"
    out_path = workdir / "proposals.jsonl"
    log_path = workdir / "proposer.log"
    with in_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    memo_path = None
    if _CACHE is not None:  # audit runs only: reuse a deterministic proposer's earlier output
        memo_path = _CACHE.proposal_dir() / f"{_audit_fingerprint(script, in_path)}.jsonl"
        if memo_path.exists():
            shutil.copy(memo_path, out_path)
            return _parse_output(out_path, "ok (memo)")
    # The decisive limit is CPU time summed over the proposer's process tree, so
    # the verdict does not depend on machine load.  The wall-clock backstop only
    # stops a proposer that hangs; it sits far above any CPU-bound run.
    cpu_limit = proposer_cpu_limit(config, len(rows))
    wall_backstop = float(config.get("proposer_wall_factor", 10)) * cpu_limit + 300.0

    def _rlimit():
        hard = int(cpu_limit) + 30
        resource.setrlimit(resource.RLIMIT_CPU, (int(cpu_limit) + 5, hard))

    started = time.time()
    cpu_before = _children_cpu()
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            ["bash", str(script), str(in_path), str(out_path)],
            cwd=str(ROOT),
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            preexec_fn=_rlimit,
        )
        try:
            code = proc.wait(timeout=wall_backstop)
        except subprocess.TimeoutExpired:
            code = None
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(proc.pid, signal.SIGKILL)
        if code is None:
            proc.wait()
    cpu_used = _children_cpu() - cpu_before
    elapsed = time.time() - started
    if code is None:
        return None, f"proposer did not finish within the {wall_backstop:.0f}s wall-clock backstop"
    if cpu_used > cpu_limit:
        return None, f"proposer used {cpu_used:.0f}s of CPU time, above its limit of {cpu_limit:.0f}s"
    if code != 0:
        return None, f"proposer exited with status {code}"
    if not out_path.exists():
        return None, "proposer wrote no output file"
    if memo_path is not None:
        shutil.copy(out_path, memo_path)
    return _parse_output(out_path, f"ok (cpu {cpu_used:.1f}s of {cpu_limit:.0f}s, wall {elapsed:.0f}s)")


def _parse_output(out_path: Path, message: str):
    rows_out = []
    try:
        for line in out_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows_out.append(json.loads(line))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, f"malformed output: {exc}"
    return rows_out, message


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


def evaluate_proposer(name, script, problems, coords, exp, config, workers):
    """Returns (metrics or None if the run failed, details)."""
    rows = proposer_input(problems, coords, exp, config)
    workdir = Path(tempfile.mkdtemp(prefix=f"hageo_eval_{SLICE}_"))
    log_tail = ""
    try:
        output, message = run_proposer(script, rows, config, workdir)
        log_file = workdir / "proposer.log"
        if log_file.exists():
            log_tail = log_file.read_text(encoding="utf-8", errors="replace")[-2000:]
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    if output is None:
        return None, {"status": f"failed: {message}", "log_tail": log_tail}
    try:
        attempts = gate.validate_rows(output, problems, int(exp["max_attempts"]), int(exp["max_aux_per_attempt"]))
    except gate.GateError as exc:
        return None, {"status": f"failed: gate violation: {exc}"}
    started = time.time()
    first, used = verify_all(problems, attempts, workers)
    return compute_metrics(first, problems, exp), {
        "status": "ok",
        "proposer": message,
        "verify_seconds": round(time.time() - started, 1),
        "first_success": first,
        "attempts_verified": used,
        "attempts_submitted": {pid: len(a) for pid, a in attempts.items()},
    }


def recompute_baselines(problems, coords, exp, config, workers) -> dict:
    out = {"_config": {k: exp[k] for k in ("max_attempts", "max_aux_per_attempt")}}
    # DDAR alone: verify each problem with no auxiliary construction.
    first, _ = verify_all(problems, {p["problem_id"]: [[]] for p in problems}, workers)
    out["ddar"] = {pid: (None if v is None else 1) for pid, v in first.items()}
    for name, rel in config["baseline_proposers"].items():
        metrics, det = evaluate_proposer(name, ROOT / rel, problems, coords, exp, config, workers)
        if metrics is None:
            raise RuntimeError(f"baseline {name} failed: {det}")
        out[name] = det["first_success"]
    return out


def main() -> None:
    global _CACHE
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--details", type=Path, default=DETAILS_OUT)
    parser.add_argument("--only", nargs="*", default=None, help="audit use: score only these proposers")
    parser.add_argument("--experiments", nargs="*", default=None, help="audit use: only these experiments")
    parser.add_argument("--cache", type=Path, default=None, help="audit use: verification/proposal cache")
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--recompute-baselines", action="store_true")
    parser.add_argument("--no-proposers", action="store_true", help="audit use: only fixed baselines")
    args = parser.parse_args()

    config = load_config()
    experiments = config["experiments"]
    if args.experiments:
        experiments = {k: v for k, v in experiments.items() if k in args.experiments}
    workers = args.workers or effective_cpus()
    if args.cache is not None:
        args.cache.parent.mkdir(parents=True, exist_ok=True)
        _CACHE = Cache(args.cache)

    import engine  # noqa: E402

    problems = {}
    coords = {}
    for exp_name, exp in experiments.items():
        problems[exp_name] = read_jsonl(resolve(exp["problems"]))
        # The drawing handed to proposers is fixed evaluator data stored with
        # each problem; it is only recomputed if a file lacks it.
        coords[exp_name] = {
            p["problem_id"]: p.get("coords") or engine.draw_coordinates(p["setup"], p["goal"], int(p["seed"]))
            for p in problems[exp_name]
        }
        print(f"[eval:{SLICE}] {exp_name}: {len(problems[exp_name])} problems, {workers} workers",
              file=sys.stderr, flush=True)

    results = {e: {} for e in experiments}
    details = {e: {} for e in experiments}
    for exp_name, exp in experiments.items():
        bpath = resolve(exp["baselines"])
        if args.recompute_baselines:
            bpath.write_text(json.dumps(recompute_baselines(problems[exp_name], coords[exp_name], exp, config,
                                                            workers), indent=1, sort_keys=True) + "\n",
                             encoding="utf-8")
        baselines = json.loads(bpath.read_text(encoding="utf-8")) if bpath.exists() else {}
        for name in FIXED_BASELINES:
            if name in baselines:
                results[exp_name][name] = compute_metrics(baselines[name], problems[exp_name], exp)
                details[exp_name][name] = {"status": "ok (fixed evaluator baseline)"}

    proposers = {} if args.no_proposers else discover_proposers(args.only)
    for name, script in proposers.items():
        failed = None
        per_exp = {}
        for exp_name, exp in experiments.items():
            print(f"[eval:{SLICE}] proposer {name} on {exp_name}", file=sys.stderr, flush=True)
            try:
                metrics, det = evaluate_proposer(name, script, problems[exp_name], coords[exp_name], exp, config,
                                                 workers)
            except Exception as exc:  # noqa: BLE001 - any failure scores as a failed run
                metrics, det = None, {"status": f"failed: evaluator error {type(exc).__name__}: {exc}"}
            per_exp[exp_name] = (metrics, det)
            if metrics is None:
                failed = f"{exp_name}: {det['status']}"
                break
        for exp_name, exp in experiments.items():
            metrics, det = per_exp.get(exp_name, (None, {"status": "not run"}))
            if failed is not None:
                # A failed run scores the worst value in every metric of every experiment.
                metrics = worst_metrics(exp)
                det = dict(det, status=f"failed: {failed}")
            results[exp_name][name] = metrics
            details[exp_name][name] = det
            print(f"[eval:{SLICE}] {name} {exp_name}: {det['status']} {metrics}", file=sys.stderr, flush=True)

    scores = {"slice": SLICE, "experiments": {}}
    for exp_name in experiments:
        scores["experiments"][exp_name] = {
            "results": results[exp_name],
            "_status": {name: details[exp_name][name]["status"] for name in results[exp_name]},
        }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(scores, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.details.parent.mkdir(parents=True, exist_ok=True)
    args.details.write_text(json.dumps(details, indent=1, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
