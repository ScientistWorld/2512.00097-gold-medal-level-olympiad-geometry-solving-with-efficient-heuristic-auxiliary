#!/bin/bash
# Hardening job 2: fixed baselines, reference, audit of variants/shortcuts
# through the unchanged hidden test, then reference-only score files.
# Resumable: every DDAR verification is cached in tmp/hardening/.
set -uo pipefail
cd /home/user
export MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl PYTHONUNBUFFERED=1
H=tmp/hardening
R=redteam/hardening/results
mkdir -p $H $R outputs
CT=$H/cache_test.jsonl
CR=$H/cache_train.jsonl

restore_eval() {
  if [ -d $H/evalbak ]; then
    cp -a $H/evalbak/test/. eval/test/
    cp -a $H/evalbak/train/. eval/train/
    rm -rf $H/evalbak
  fi
  rm -f proposers/hageo_*.sh proposers/sc_*.sh proposers/systematic.sh
}
backup_eval() {
  mkdir -p $H/evalbak/test $H/evalbak/train
  cp -a eval/test/problems.jsonl eval/test/config.json eval/test/baselines.json $H/evalbak/test/
  cp -a eval/train/config.json eval/train/baselines.json $H/evalbak/train/
}
final_scores() {
  echo "[job] reference-only score files $(date)"
  EVAL_CACHE=$CR bash scripts/evaluate_train.sh
  cp scoring/scores_train.json scoring/scores.json
  EVAL_CACHE=$CT bash scripts/evaluate_test.sh
  cp scoring/scores_test.json $R/final_scores_test.json; cp scoring/scores_train.json $R/final_scores_train.json
}
restore_eval   # in case an earlier run was killed mid-audit

echo "[job] stage 1: fixed baselines $(date)"
[ -s eval/test/baselines.json ] || python eval/test/evaluate.py --recompute-baselines --no-proposers \
  --cache $CT --out $R/baselines_test_scores.json --details $R/baselines_test_details.json
[ -s eval/train/baselines.json ] || python eval/train/evaluate.py --recompute-baselines --no-proposers \
  --cache $CR --out $R/baselines_train_scores.json --details $R/baselines_train_details.json

echo "[job] stage 2: reference through the real scripts $(date)"
EVAL_CACHE=$CT bash scripts/evaluate_test.sh && cp scoring/scores_test.json $R/reference_scores_test.json && cp outputs/eval_test_details.json $R/reference_details_test.json
EVAL_CACHE=$CR bash scripts/evaluate_train.sh && cp scoring/scores_train.json $R/reference_scores_train.json && cp outputs/eval_train_details.json $R/reference_details_train.json

echo "[job] stage 3a: audit (key variants + cheap shortcuts) via no-arg hidden test $(date)"
backup_eval
for f in hageo_seed1 hageo_ranked hageo_unfiltered systematic sc_constant_flags sc_no_aux sc_overdetermined \
         sc_stale_coords sc_too_many sc_empty_output sc_crash sc_direct_scores sc_tamper_eval; do
  cp redteam/hardening/registry/$f.sh proposers/
done
EVAL_CACHE=$CT bash scripts/evaluate_test.sh; echo "[job] hidden test exit $?"
cp scoring/scores_test.json $R/audit_a_scores_test.json; cp outputs/eval_test_details.json $R/audit_a_details_test.json
restore_eval
final_scores

echo "[job] stage 3b: audit (all variants + goal-lookup private search) $(date)"
backup_eval
cp redteam/hardening/registry/*.sh proposers/
EVAL_CACHE=$CT bash scripts/evaluate_test.sh; echo "[job] hidden test exit $?"
cp scoring/scores_test.json $R/audit_scores_test.json; cp outputs/eval_test_details.json $R/audit_details_test.json
restore_eval
final_scores

echo "[job] stage 4: train side for the main variants $(date)"
for f in hageo_seed1 hageo_ranked hageo_unfiltered systematic hageo_n1 hageo_n3; do cp redteam/hardening/registry/$f.sh proposers/; done
EVAL_CACHE=$CR bash scripts/evaluate_train.sh
cp scoring/scores_train.json $R/audit_scores_train.json; cp outputs/eval_train_details.json $R/audit_details_train.json
restore_eval

final_scores
echo "[job] done $(date)"
