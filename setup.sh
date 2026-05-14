#!/usr/bin/env bash
# Install dependencies and prepare the project.
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
    echo "[ERROR] uv is not installed. Install it from https://docs.astral.sh/uv/" >&2
    exit 1
fi

cd "$(dirname "$0")"
uv sync
