#!/bin/bash
cd "$(dirname "$0")/.."
exec python redteam/hardening/proposers/shortcuts.py crash "$1" "$2"
