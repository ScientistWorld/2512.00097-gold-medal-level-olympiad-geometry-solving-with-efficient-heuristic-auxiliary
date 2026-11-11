#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec python redteam/hardening/proposers/systematic.py "$1" "$2"
