#!/usr/bin/env bash
# Kleiner Wrapper: setzt den uv-PATH, sorgt fuer eine WSL-eigene .venv und
# ruft vhs aus dem Repo-Root. Aufruf von Windows:
#   wsl -d Ubuntu-22.04 -- bash /mnt/c/Users/Michael/Repos/codename-generator/demo/render-wsl.sh <tape>
set -euo pipefail

TAPE="${1:-demo/intro.tape}"

export PATH="$HOME/.local/bin:$PATH"
cd /mnt/c/Users/Michael/Repos/codename-generator

# Die .venv im /mnt/c-Mount ist langsam (NTFS via 9P) und wenn sie unter
# Windows mit Python aus C:\Python313 angelegt wurde, schlaegt sie in Linux
# fehl. Stattdessen die .venv im Linux-Home anlegen und uv darauf zeigen.
WSL_VENV="$HOME/.venvs/codename-generator"
export UV_PROJECT_ENVIRONMENT="$WSL_VENV"
mkdir -p "$(dirname "$WSL_VENV")"

if [ ! -f "$WSL_VENV/bin/python" ]; then
    echo "==> Erstelle WSL-eigene .venv unter $WSL_VENV"
    uv sync --quiet
fi

vhs "$TAPE"
