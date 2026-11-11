#!/bin/bash
cd "$(dirname "$0")/.."
exec python redteam/hardening/proposers/shortcuts.py too_many "$1" "$2"
