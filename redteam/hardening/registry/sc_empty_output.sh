#!/bin/bash
cd "$(dirname "$0")/.."
exec python redteam/hardening/proposers/shortcuts.py empty_output "$1" "$2"
