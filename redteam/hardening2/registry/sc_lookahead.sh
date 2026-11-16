#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec python redteam/hardening2/proposers/lookahead.py "$1" "$2"
