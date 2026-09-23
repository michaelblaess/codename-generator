"""Einstellungsseite (Taste s / F2).

Erbt von `BaseSettingsScreen` aus textual-widgets. Den Sprach-Tab der Basis
blendet sie aus: die Oberflaeche der TUI ist englisch, und der Schluessel
"language" bedeutet hier die Sprache der erzeugten Namen - die wechselt im
Einstellungspanel sofort und braucht keinen Neustart.

Die Namenswahl, Mutation, Wortzahl und Vorschlagsanzahl bleiben im Panel
links, wo sie beim Suchen gebraucht werden. Hier steht nur, was selten
angefasst wird: die Tastatur und der Speicherort.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Checkbox, Label, Select, Static, TabPane
from textual_widgets import BaseSettingsScreen

from codename_generator import settings as settings_module

KEYMAP_STYLE_OPTIONS: list[tuple[str, str]] = [
    ("By operating system", ""),
    ("Classic (letters only)", "classic"),
    ("With function keys (F1-F10)", "function_keys"),
]
"""Leer heisst "noch nicht entschieden" - dann schlaegt die Plattform den Stil vor."""


class CodenameSettingsScreen(BaseSettingsScreen):  # type: ignore[misc]
    """Einstellungen: Tastatur-Layout, Vim-Navigation, Speicherort."""

    SHOW_LANGUAGE_TAB = False

    def app_tabs(self) -> ComposeResult:
        """Der Tab "Keyboard"."""
        style = str(self._settings.get("keymap_style", "") or "")
        if style not in {value for _, value in KEYMAP_STYLE_OPTIONS}:
            style = ""
        with TabPane("Keyboard", id="settings-tab-keyboard"), VerticalScroll():
            with Horizontal(classes="settings-row"):
                yield Label("Layout:")
                yield Select[str](
                    KEYMAP_STYLE_OPTIONS,
                    value=style,
                    allow_blank=False,
                    id="set-keymap-style",
                )
            with Horizontal(classes="settings-row"):
                yield Label("Vim:")
                checkbox = Checkbox(
                    "Vim navigation in the suggestion table",
                    value=bool(self._settings.get("keymap_vim", False)),
                    id="set-keymap-vim",
                )
                checkbox.tooltip = (
                    "j and k move the cursor, g and G jump to the first and last row, "
                    "Ctrl+D and Ctrl+U page. Only while the table has the focus."
                )
                yield checkbox
            yield Static(
                "Keyboard changes take effect after a restart. "
                "Own key bindings: settings.json, section keymap_custom. "
                "Press ? to see every key that is bound right now.",
                classes="settings-hint",
            )

    def collect_app_settings(self, settings: dict[str, object]) -> None:
        """Schreibt Stil und Vim-Schalter ins Ergebnis."""
        style = self.query_one("#set-keymap-style", Select).value
        if isinstance(style, str):
            settings["keymap_style"] = style
        settings["keymap_vim"] = self.query_one("#set-keymap-vim", Checkbox).value

    def storage_paths(self) -> list[tuple[str, Path]]:
        """Die settings.json - Favoriten, eigenes Wort, Tastatur."""
        # Zur Laufzeit gelesen, damit Tests den Pfad umbiegen koennen.
        return [("Settings", settings_module._SETTINGS_FILE)]
