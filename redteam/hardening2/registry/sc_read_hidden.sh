#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec python redteam/hardening2/proposers/rules.py read_hidden "$1" "$2"
