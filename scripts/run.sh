#!/bin/bash
# Regenerate solver artifacts, then score the canonical, train, and held-out
# evaluation views.

set -e

cd /home/user

bash scripts/reproduce.sh
bash scripts/evaluate.sh
bash scripts/evaluate_train.sh /home/user/checkpoints
bash scripts/evaluate_test.sh /home/user/checkpoints
