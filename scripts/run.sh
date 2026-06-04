#!/bin/bash
# Score the visible train split and held-out test split from existing solver
# artifacts under outputs/.

set -e

cd /home/user

bash scripts/evaluate_train.sh /home/user/checkpoints
bash scripts/evaluate_test.sh /home/user/checkpoints
