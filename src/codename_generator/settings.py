from __future__ import annotations

import json
from pathlib import Path

_SETTINGS_DIR = Path.home() / ".codename-generator"
_SETTINGS_FILE = _SETTINGS_DIR / "settings.json"


class JsonSettingsStore:
    """Persistiert App-Einstellungen als JSON in ~/.codename-generator/."""

    def load(self) -> dict[str, object]:
        """Laedt die Einstellungen. Leeres Dict wenn Datei fehlt oder defekt."""
        if not _SETTINGS_FILE.is_file():
            return {}
        try:
            data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return data if isinstance(data, dict) else {}

    def save(self, settings: dict[str, object]) -> None:
        """Schreibt die Einstellungen. Fehler werden still verschluckt."""
        try:
            _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            _SETTINGS_FILE.write_text(
                json.dumps(settings, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass
