#!/usr/bin/env bash
# Setup VHS + ttyd + ffmpeg + uv im WSL Ubuntu 22.04, damit demo/*.tape
# Files lokal gerendert werden koennen.
#
# Aufruf (im WSL Ubuntu Shell):
#   bash /mnt/c/Users/Michael/Repos/codename-generator/demo/install-wsl.sh
#
# Erwartet ein interaktives sudo-Prompt.
set -euo pipefail

if [ ! -f /etc/lsb-release ]; then
    echo "Erwarte Ubuntu/Debian-WSL." >&2
    exit 1
fi

echo "==> apt update + ffmpeg + Chromium-Dependencies"
sudo apt-get update -qq
# VHS startet Chromium ueber rod - der zieht ein eigenes Browser-Binary, das
# aber die System-Libs braucht (libnss3, libgtk-3 usw.). Ubuntu 22.04 hat die
# nicht standardmaessig drin.
sudo apt-get install -y --no-install-recommends \
    ffmpeg curl ca-certificates \
    libnss3 libxkbcommon0 libasound2 \
    libatk-bridge2.0-0 libdrm2 libgbm1 libgtk-3-0

# ttyd >= 1.7.2 ist Voraussetzung fuer vhs - Ubuntu 22.04 liefert nur 1.6.3,
# darum apt-Paket entfernen und das Upstream-Binary nach /usr/local/bin legen.
TTYD_VER="1.7.7"
if command -v ttyd >/dev/null 2>&1 && ttyd --version 2>&1 | grep -q "$TTYD_VER"; then
    echo "==> ttyd v$TTYD_VER bereits installiert"
else
    echo "==> ttyd-Upstream v$TTYD_VER installieren (apt-Paket ist zu alt)"
    sudo apt-get remove -y ttyd 2>/dev/null || true
    sudo curl -fsSL -o /usr/local/bin/ttyd \
        "https://github.com/tsl0922/ttyd/releases/download/${TTYD_VER}/ttyd.x86_64"
    sudo chmod +x /usr/local/bin/ttyd
fi

VHS_VER="0.11.0"
if command -v vhs >/dev/null 2>&1 && vhs --version 2>/dev/null | grep -q "$VHS_VER"; then
    echo "==> vhs v$VHS_VER bereits installiert"
else
    echo "==> Lade vhs v$VHS_VER .deb von github.com/charmbracelet/vhs"
    DEB=$(mktemp --suffix=.deb)
    curl -fsSL -o "$DEB" \
        "https://github.com/charmbracelet/vhs/releases/download/v${VHS_VER}/vhs_${VHS_VER}_amd64.deb"
    sudo dpkg -i "$DEB"
    rm -f "$DEB"
fi

if command -v uv >/dev/null 2>&1; then
    echo "==> uv bereits installiert ($(uv --version))"
else
    echo "==> Installiere uv (astral.sh)"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # uv landet in ~/.local/bin - in PATH ergaenzen, falls noch nicht.
    if ! grep -q "/.local/bin" "$HOME/.bashrc" 2>/dev/null; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    fi
    export PATH="$HOME/.local/bin:$PATH"
fi

echo
echo "==> Verifikation"
which vhs ttyd ffmpeg
"$HOME/.local/bin/uv" --version 2>/dev/null || uv --version

echo
echo "Done. Test mit:"
echo "  cd /mnt/c/Users/Michael/Repos/codename-generator"
echo "  vhs demo/intro.tape"
