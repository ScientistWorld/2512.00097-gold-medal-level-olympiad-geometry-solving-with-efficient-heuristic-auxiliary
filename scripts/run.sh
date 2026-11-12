#!/bin/bash
# Hardening job 3 (preemption-robust: completed stages leave markers, every
# DDAR verification and proposer output is cached under tmp/hardening/).
#  J: screen JGEX-231 with DDAR alone, build its train/test split, baselines
#  2: reference through the real evaluate scripts (both experiments)
#  3: audit variants + shortcuts through the unchanged no-arg hidden test
#  4: train side for the main variants
#  F: reference-only score files
set -uo pipefail
cd /home/user
export MPLBACKEND=Agg MPLCONFIGDIR=/tmp/mpl PYTHONUNBUFFERED=1
H=tmp/hardening
R=redteam/hardening/results
mkdir -p $H $R outputs
CT=$H/cache_test.jsonl
CR=$H/cache_train.jsonl
done_() { [ -e $H/done_$1 ]; }
mark() { touch $H/done_$1; }

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
  cp -a eval/test/*.jsonl eval/test/*.json $H/evalbak/test/
  cp -a eval/train/*.json $H/evalbak/train/
}
final_scores() {
  echo "[job] reference-only score files $(date)"
  EVAL_CACHE=$CR bash scripts/evaluate_train.sh && cp scoring/scores_train.json scoring/scores.json
  EVAL_CACHE=$CT bash scripts/evaluate_test.sh
  cp scoring/scores_test.json $R/final_scores_test.json; cp scoring/scores_train.json $R/final_scores_train.json
}
restore_eval

if ! done_ jgex_split; then
  echo "[job] J: screen + split JGEX-231 $(date)"
  timeout 2400 python eval/test/build_split.py screen --source jgex --timeout 6 --max-points 13 --budget-seconds 2000
  python eval/test/build_split.py split --source jgex --sat-max 4.0 --test-fraction 0.6 --test-budget 1e9 --train-budget 1e9 \
    && mark jgex_split
fi
if ! done_ jgex_baselines; then
  echo "[job] J: JGEX fixed baselines $(date)"
  python eval/test/evaluate.py --experiments jgex231_aux --recompute-baselines --no-proposers --cache $CT \
    --out $R/baselines_jgex_test_scores.json --details $R/baselines_jgex_test_details.json && \
  python eval/train/evaluate.py --experiments jgex231_aux --recompute-baselines --no-proposers --cache $CR \
    --out $R/baselines_jgex_train_scores.json --details $R/baselines_jgex_train_details.json && mark jgex_baselines
fi

if ! done_ reference; then
  echo "[job] 2: reference through the real scripts $(date)"
  EVAL_CACHE=$CT bash scripts/evaluate_test.sh && cp scoring/scores_test.json $R/reference_scores_test.json \
    && cp outputs/eval_test_details.json $R/reference_details_test.json && \
  EVAL_CACHE=$CR bash scripts/evaluate_train.sh && cp scoring/scores_train.json $R/reference_scores_train.json \
    && cp outputs/eval_train_details.json $R/reference_details_train.json && mark reference
fi

if ! done_ audit; then
  echo "[job] 3: audit via no-arg hidden test $(date)"
  backup_eval
  cp redteam/hardening/registry/*.sh proposers/
  EVAL_CACHE=$CT bash scripts/evaluate_test.sh; rc=$?
  echo "[job] hidden test exit $rc"
  cp scoring/scores_test.json $R/audit_scores_test.json; cp outputs/eval_test_details.json $R/audit_details_test.json
  restore_eval
  [ $rc -eq 0 ] && mark audit
  final_scores
fi

if ! done_ train_audit; then
  echo "[job] 4: train side for the main variants $(date)"
  for f in hageo_seed1 hageo_ranked systematic hageo_unfiltered; do cp redteam/hardening/registry/$f.sh proposers/; done
  EVAL_CACHE=$CR bash scripts/evaluate_train.sh && cp scoring/scores_train.json $R/audit_scores_train.json \
    && cp outputs/eval_train_details.json $R/audit_details_train.json && mark train_audit
  restore_eval
fi

final_scores
echo "[job] done $(date)"
