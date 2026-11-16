#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec python method/hageo/propose.py "$1" "$2" --rounds 2 --seed 2
