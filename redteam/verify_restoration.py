#!/usr/bin/env python3
"""Read-only checks of the gym, plus a saved audit verification record."""
import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path('/home/user')
RT = ROOT / 'redteam'
initial_state = json.loads((RT / 'initial_state.json').read_text())
initial = initial_state['head']
initial_dirty = [line[3:] for line in initial_state['initial_status'].splitlines()
                 if line[:2] != '??']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


paths = ['.', *[f':(exclude){path}' for path in initial_dirty], ':(exclude)redteam',
         ':(exclude)REDTEAM.md', ':(exclude)action.yaml']
changed = subprocess.check_output(
    ['git', 'diff', '--name-only', initial, '--', *paths], cwd=ROOT, text=True
).splitlines()
assert not changed, changed

preserved = {}
for directory in ('outputs', 'data/benchmarks', 'scoring'):
    for original in sorted((RT / 'originals' / directory).glob('*')):
        actual = ROOT / directory / original.name
        preserved[f'{directory}/{original.name}'] = {
            'sha256': digest(actual), 'matches_original': digest(actual) == digest(original)
        }
assert all(value['matches_original'] for value in preserved.values())
assert not (ROOT / 'method/audit_submission.py').exists()
assert set(p.name for p in (ROOT / 'outputs').glob('*.jsonl')) == set(
    p.name for p in (RT / 'originals/outputs').glob('*.jsonl'))

for script in sorted(RT.glob('*.py')):
    ast.parse(script.read_text(), filename=str(script))
cases = []
for script in sorted(RT.glob('*/run.sh')):
    subprocess.run(['bash', '-n', str(script)], check=True)
    folder = script.parent
    status = json.loads((folder / 'status.json').read_text())
    assert status['name'] == folder.name
    stage = status['stages'].get('test', {})
    assert stage.get('returncode') in (0, 1), status
    assert (folder / 'scores_test.json').exists() == (stage['returncode'] == 0)
    cases.append({'name': folder.name, 'test_exit': stage['returncode']})

record = {
    'initial_git_commit': initial,
    'unexpected_tracked_gym_differences': changed,
    'excluded_initial_infrastructure_changes': initial_dirty,
    'excluded_required_control_file': 'action.yaml',
    'installed_submission_removed': True,
    'original_artifacts': preserved,
    'case_shell_and_python_syntax': 'passed',
    'cases': cases,
}
(RT / 'verification.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
print(f'Verified restored gym and {len(cases)} completed case records.')
