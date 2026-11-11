#!/bin/bash
cd "$(dirname "$0")/.."
exec python redteam/hardening/proposers/shortcuts.py no_aux "$1" "$2"
