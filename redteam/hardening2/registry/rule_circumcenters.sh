#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec python redteam/hardening2/proposers/rules.py circumcenters3 "$1" "$2"
