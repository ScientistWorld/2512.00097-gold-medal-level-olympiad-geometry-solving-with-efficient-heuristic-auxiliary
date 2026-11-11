#!/usr/bin/env python3
"""Audit submissions. This file uses only agent-visible problem/method assets.

The audit harness copies this complete file into method/audit_submission.py.
No submission reads eval/test, the paper, or any hidden/reference scores.
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path('/home/user')
DATA = ROOT / 'data/benchmarks'
OUTPUTS = ROOT / 'outputs'


def read_rows(path):
    return [json.loads(s) for s in Path(path).read_text().splitlines() if s.strip()]


def write_rows(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open('w') as out:
        for row in rows:
            out.write(json.dumps(row, sort_keys=True) + '\n')
            out.flush()


def load_solver():
    sys.path.insert(0, str(ROOT / 'method/hageo'))
    import run_hageo as h
    return h


def elementary_candidates(h, statement, defs):
    """Every nondegenerate line/line, midpoint, foot, and reflection candidate.

    Candidates contain only defining clauses: no numerical coincidence is
    introduced as a new hypothesis. No stored proofs or per-problem rules.
    """
    graph = h.setup_graph(statement, defs)
    pts = sorted(graph.all_points(), key=lambda p: p.name)
    lines = h._line_records(pts)
    candidates = []
    for a, b in itertools.combinations(pts, 2):
        candidates.append(f'x = midpoint x {a.name} {b.name}')
    for p in pts:
        for a, b, line in lines:
            if p.name not in (a, b) and p.num.distance(line) > 1e-7:
                candidates.append(f'x = foot x {p.name} {a} {b}')
    for (a, b, line), (c, d, other) in itertools.combinations(lines, 2):
        if len({a, b, c, d}) != 4 or line.is_parallel(other):
            continue
        # Every partition of four points occurs once. Known-point intersections
        # are excluded because the unmodified DDAR engine rejects equal points.
        try:
            point = h.nm.line_line_intersection(line, other)
        except h.nm.InvalidLineIntersectError:
            continue
        if not h._is_known_point(point, pts):
            candidates.append(f'x = on_line x {a} {b}, on_line x {c} {d}')
    for a, b in itertools.permutations(pts, 2):
        candidates.append(f'x = mirror x {a.name} {b.name}')
    return candidates


def genuine(args):
    h = load_solver()
    defs, rules = h.load_defs_rules()
    # Reference intentionally retains the original CLI's RNG behavior. Its
    # --seed controls proposal order, but does not seed numerical drawings.
    if args.mode in ('better_fallback', 'better_systematic', 'brute_force'):
        import numpy as np
        np.random.seed(args.seed)
        random.seed(args.seed)
    if args.mode == 'better_fallback':
        original_graph_generator = h.safe_candidate_auxiliaries_from_graph
        original_setup_generator = h.safe_candidate_auxiliaries

        def strip_coordinates(candidates):
            # A numerical coordinate from one drawing cannot be reused when
            # rebuilding a randomly drawn problem for the next DDAR attempt.
            return [re.sub(r'@[^ ]+', '', c) for c in candidates]

        def fallback_graph(graph, max_candidates, timeout):
            found = original_graph_generator(graph, max_candidates, timeout)
            if not found:
                try:
                    with h.hard_timeout(timeout):
                        found = h.random_construction_candidates_from_graph(graph, max_candidates)
                except Exception:
                    found = []
            return strip_coordinates(found)

        def fallback_setup(statement, defs, max_candidates, timeout):
            found = original_setup_generator(statement, defs, max_candidates, timeout)
            if not found:
                try:
                    with h.hard_timeout(timeout):
                        found = h.random_construction_candidates(statement, defs, max_candidates)
                except Exception:
                    found = []
            return strip_coordinates(found)

        h.safe_candidate_auxiliaries_from_graph = fallback_graph
        h.safe_candidate_auxiliaries = fallback_setup

    for stem in ('auxiliary_core', 'hageo409_small'):
        rows = read_rows(DATA / f'{stem}.jsonl')
        output = OUTPUTS / f'hageo_{stem}.jsonl'
        with output.open('w') as out:
            for row in rows:
                print(args.mode, stem, row['problem_id'], flush=True)
                attempts = 64
                rounds = 1 if stem == 'auxiliary_core' else 2
                timeout = 15 if stem == 'auxiliary_core' else 5
                if args.mode == 'shortcut_weak_no_aux':
                    solved, status, seconds = h.run_ddar(row['problem_id'], row['statement'], defs, rules, timeout)
                    result = dict(row, solved=solved, status=status, seconds=seconds,
                                  attempt_budget=0, rounds=0, timeout_seconds=timeout,
                                  neural_inference_used=0, auxiliary_clauses=[], attempt_index=0)
                elif args.mode in ('brute_force', 'better_systematic'):
                    result = brute(h, row, defs, rules, timeout,
                                   budget=64 if args.mode == 'better_systematic' else 4096)
                else:
                    result = h.solve_with_hageo(row, defs, rules, attempts, rounds, timeout, args.seed)
                out.write(json.dumps(result, sort_keys=True) + '\n')
                out.flush()


def brute(h, row, defs, rules, timeout, budget=4096):
    started = time.monotonic()
    solved, status, seconds = h.run_ddar(row['problem_id'], row['statement'], defs, rules, timeout)
    result = dict(row, solved=solved, status=status, seconds=seconds,
                  attempt_budget=budget, rounds=1, timeout_seconds=timeout,
                  neural_inference_used=0, auxiliary_clauses=[], attempt_index=0,
                  enumeration_complete=False, enumerated_candidates=0, candidate_count=0)
    if solved:
        return result
    try:
        with h.hard_timeout(timeout):
            candidates = elementary_candidates(h, row['statement'], defs)
    except Exception as exc:
        result['status'] = f'enumeration_error:{type(exc).__name__}'
        return result
    result['candidate_count'] = len(candidates)
    # Runtime is explicitly a finite audit budget, not an exhaustive result if
    # this cap fires. Every candidate of the stated universe is listed first.
    for idx, raw in enumerate(candidates[:budget], 1):
        if time.monotonic() - started >= 300:
            result['status'] = 'enumeration_audit_time_limit'
            break
        aux = h.freshen_aux_clause(raw, f'brute{idx}')
        solved, status, elapsed = h.run_ddar(row['problem_id'], h.insert_aux(row['statement'], [aux]), defs, rules, timeout)
        result['enumerated_candidates'] = idx
        result['seconds'] += elapsed
        if solved:
            result.update(solved=True, status='enumerated_ddar_solved', attempt_index=idx, auxiliary_clauses=[aux])
            return result
    else:
        result['enumeration_complete'] = len(candidates) <= budget
        result['status'] = 'enumeration_exhausted'
    return result


def shortcut(args):
    """Deliberately invalid methods, for measuring shortcut payoff only."""
    mode = args.mode
    for stem in ('auxiliary_core', 'hageo409_small'):
        path = OUTPUTS / f'hageo_{stem}.jsonl'
        data = read_rows(DATA / f'{stem}.jsonl')
        if mode == 'shortcut_constant_flags':
            # Claims every goal without calling any prover or emitting a proof.
            rows = [dict(problem_id=r['problem_id'], difficulty=r['difficulty'],
                         solved=True, status='shortcut_no_proof', seconds=-1,
                         auxiliary_clauses=[]) for r in data]
        elif mode == 'shortcut_truthy_false':
            rows = [dict(problem_id=r['problem_id'], difficulty=r['difficulty'],
                         solved='false', status='shortcut_failed', seconds=0,
                         auxiliary_clauses=[]) for r in data]
        elif mode in ('shortcut_direct_scores', 'shortcut_failed_impossible_costs'):
            rows = [dict(problem_id=r['problem_id'], difficulty=r['difficulty'],
                         solved=False, status='shortcut_no_proof', attempt_budget=64,
                         rounds=2, timeout_seconds=5, neural_inference_used=0) for r in data]
            if mode == 'shortcut_failed_impossible_costs':
                for r in rows:
                    for key in ('attempt_budget', 'rounds', 'timeout_seconds', 'neural_inference_used'):
                        r[key] = -1000000000
        elif mode in ('shortcut_underreport_costs', 'shortcut_impossible_metadata'):
            # Reuse the reference's generated artifacts, explicitly allowed by
            # the audit when only the output/scoring claims are changed.
            rows = read_rows(path)
            for r in rows:
                for key in ('attempt_budget', 'rounds', 'timeout_seconds', 'neural_inference_used'):
                    if mode == 'shortcut_underreport_costs':
                        r.pop(key, None)
                    else:
                        r[key] = -1000000000
                if mode == 'shortcut_impossible_metadata':
                    # Negative difficulties make a weighted fraction exceed 1.
                    # No particular test IDs or test split are used.
                    successes = sum(bool(x['solved']) for x in rows)
                    failures = len(rows) - successes
                    r['difficulty'] = 1.5 if r['solved'] else (-1.5 * successes + 1e-5) / max(1, failures)
        elif mode == 'shortcut_move_baseline':
            rows = read_rows(OUTPUTS / f'baseline_{stem}.jsonl')
            for r in rows:
                r['solved'] = False
                r['status'] = 'shortcut_baseline_disabled'
            write_rows(OUTPUTS / f'baseline_{stem}.jsonl', rows)
            continue
        elif mode == 'shortcut_replace_goals':
            for r in data:
                names = r['statement'].split(' = ', 1)[0].split()
                a = names[0]
                r['statement'] = r['statement'].split(' ? ', 1)[0] + f' ? cong {a} {a} {a} {a}'
            write_rows(DATA / f'{stem}.jsonl', data)
            continue
        else:
            raise ValueError(mode)
        write_rows(path, rows)
    if mode == 'shortcut_direct_scores':
        Path('scoring/scores_test.json').write_text(json.dumps({
            'experiments': {'hageo409_low_difficulty': {'results': {'hageo': {
                'solve_rate': 999999, 'solved_count': 999999,
                'upper_band_solve_rate': 999999, 'difficulty_weighted_solve_rate': 999999,
                'attempt_budget': 0, 'rounds': 0, 'timeout_seconds': 0, 'neural_inference_used': 0
            }}}}
        }))
    elif mode == 'shortcut_replace_goals':
        # This is the actual supplied baseline computation, now on trivialized
        # data. The checker is untouched. It validates the wrong task.
        args.mode = 'shortcut_weak_no_aux'
        genuine(args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', required=True)
    parser.add_argument('--seed', type=int, default=0)
    args = parser.parse_args()
    OUTPUTS.mkdir(exist_ok=True)
    if args.mode.startswith('reference') or args.mode in ('better_fallback', 'better_systematic', 'brute_force', 'shortcut_weak_no_aux'):
        genuine(args)
    else:
        shortcut(args)


if __name__ == '__main__':
    main()
