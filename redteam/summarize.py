#!/usr/bin/env python3
"""Summarize completed runs; metric definitions are audit-only inputs."""
from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

RT = Path('/home/user/redteam')
original = json.loads((RT / 'originals/scoring/scores_test.json').read_text())
definitions = json.loads((RT / 'originals/scoring/reference.json').read_text())['experiments']
reports = {}
for folder in sorted(RT.iterdir()):
    if not folder.is_dir() or not (folder / 'status.json').exists():
        continue
    status = json.loads((folder / 'status.json').read_text())
    reports[folder.name] = {'status': status}
    score_path = folder / 'scores_test.json'
    if score_path.exists():
        reports[folder.name]['scores'] = json.loads(score_path.read_text())


def metrics_for(report, exp):
    candidate = ('shortcut_unregistered' if report.get('status', {}).get('name') == 'shortcut_unregistered_method'
                 else 'hageo')
    return report.get('scores', {}).get('experiments', {}).get(exp, {}).get('results', {}).get(candidate, {})


def rank_cohort(names):
    sigmas = {}
    for exp, reference in original['experiments'].items():
        for metric, config in definitions[exp]['metrics'].items():
            if not abs(config['coefficient']):
                continue
            values = [metrics_for(reports[name], exp).get(metric) for name in names]
            values = [v for v in values if isinstance(v, (int, float)) and math.isfinite(v)]
            sigmas[f'{exp}/{metric}'] = statistics.pstdev(values) if len(values) > 1 else 0
    rankings = {}
    for name in names:
        terms = {}
        skipped = []
        for exp, reference in original['experiments'].items():
            ref = reference['results']['hageo']
            got = metrics_for(reports[name], exp)
            for metric, config in definitions[exp]['metrics'].items():
                coefficient = abs(config['coefficient'])
                if not coefficient:
                    continue
                key = f'{exp}/{metric}'
                if metric not in got or got[metric] is None:
                    skipped.append(key)
                    continue
                sd = sigmas[key]
                if not sd:
                    terms[key] = 0
                    continue
                direction = 1 if config['higher_is_better'] else -1
                terms[key] = definitions[exp]['weight'] * coefficient * direction * (got[metric] - ref[metric]) / sd
        rankings[name] = {'rank_delta': sum(terms.values()), 'terms': terms, 'skipped_metrics': skipped}
    return {'normalization': 'population standard deviation across named audit attempts; zero-variance metrics contribute zero',
            'names': names, 'sigma': sigmas, 'rankings': rankings}


successes = [n for n, r in reports.items() if r['status']['stages'].get('test', {}).get('returncode') == 0]
honest = [n for n in successes if n.startswith(('reference_', 'better_')) or n in ('shortcut_weak_no_aux', 'shortcut_fallback_fix', 'brute_force')]
summary = {'reference': original, 'runs': reports,
           'honest_cohort_rank': rank_cohort(honest),
           'all_completed_cohort_rank': rank_cohort(successes)}
seed_metrics = {}
for exp in original['experiments']:
    vals = [metrics_for(reports.get(f'reference_seed{s}', {}), exp) for s in range(3)]
    seed_metrics[exp] = {}
    for metric in definitions[exp]['metrics']:
        numbers = [v[metric] for v in vals if metric in v]
        if numbers:
            seed_metrics[exp][metric] = {'values': numbers, 'min': min(numbers), 'max': max(numbers),
                                       'spread': max(numbers) - min(numbers)}
summary['seed_spread'] = seed_metrics
(RT / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
print('case\ttest_exit\tsolved\tupper\tweighted\tattempts\trounds\ttimeout\tneural\tall_cohort_delta')
for name, report in reports.items():
    m = metrics_for(report, 'hageo409_low_difficulty')
    delta = summary['all_completed_cohort_rank']['rankings'].get(name, {}).get('rank_delta')
    print('\t'.join(map(str, [name, report['status']['stages'].get('test', {}).get('returncode'),
                              m.get('solved_count'), m.get('upper_band_solve_rate'), m.get('difficulty_weighted_solve_rate'),
                              m.get('attempt_budget'), m.get('rounds'), m.get('timeout_seconds'), m.get('neural_inference_used'), delta])))
