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

if ! done_ audit2; then
  echo "[job] 5: hybrid variant + variants/shortcuts via no-arg hidden test $(date)"
  backup_eval
  for f in redteam/hardening/registry/*.sh; do
    case "$f" in *sc_goal_lookup.sh) ;; *) cp "$f" proposers/ ;; esac
  done
  EVAL_CACHE=$CT bash scripts/evaluate_test.sh; rc=$?
  echo "[job] hidden test exit $rc"
  cp scoring/scores_test.json $R/audit2_scores_test.json; cp outputs/eval_test_details.json $R/audit2_details_test.json
  restore_eval
  [ $rc -eq 0 ] && mark audit2
fi
if ! done_ train_audit2; then
  echo "[job] 5: train side for the hybrid variant $(date)"
  for f in hageo_hybrid hageo_ranked hageo_seed1 systematic hageo_unfiltered; do cp redteam/hardening/registry/$f.sh proposers/; done
  EVAL_CACHE=$CR bash scripts/evaluate_train.sh && cp scoring/scores_train.json $R/audit2_scores_train.json \
    && cp outputs/eval_train_details.json $R/audit2_details_train.json && mark train_audit2
  restore_eval
fi

final_scores
echo "[job] done $(date)"
