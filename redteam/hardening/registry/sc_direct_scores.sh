#!/bin/bash
cd "$(dirname "$0")/.."
exec python redteam/hardening/proposers/shortcuts.py direct_scores "$1" "$2"
