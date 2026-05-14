#!/usr/bin/env bash
# Launch the codename generator. Args are forwarded to the CLI/TUI.
set -euo pipefail
cd "$(dirname "$0")"
exec uv run codename "$@"
