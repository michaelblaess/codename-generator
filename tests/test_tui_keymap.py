"""Tastenbelegung in der echten TUI: Info, Uebersicht, Einstellungen, Vim.

Settings liegen in einem temporaeren Ordner - die echte settings.json bleibt
unangetastet.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from textual.widgets import Checkbox, DataTable, Select
from textual_widgets import AboutScreen

from codename_generator import settings as settings_module
from codename_generator.keymap_screen import KeymapScreen
from codename_generator.settings_screen import CodenameSettingsScreen
from codename_generator.tui import CodenameApp, SuggestionsTable


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(settings_module, "_SETTINGS_DIR", tmp_path)
    monkeypatch.setattr(settings_module, "_SETTINGS_FILE", settings_file)
    return settings_file


def _schreibe(datei: Path, daten: dict[str, object]) -> None:
    datei.write_text(json.dumps(daten), encoding="utf-8")


def test_f1_und_i_oeffnen_info_fragezeichen_die_uebersicht(isolated_settings: Path) -> None:
    _schreibe(isolated_settings, {"keymap_style": "function_keys"})

    async def run() -> None:
        app = CodenameApp()
        async with app.run_test(size=(150, 45)) as pilot:
            for taste in ("f1", "i"):
                await pilot.press(taste)
                await pilot.pause()
                assert isinstance(app.screen, AboutScreen), taste
                await pilot.press("escape")
                await pilot.pause()
            await pilot.press("question_mark")
            await pilot.pause()
            assert isinstance(app.screen, KeymapScreen)
            zeilen = app.screen.query_one("#keymap-table", DataTable).row_count
            assert zeilen == len(app._keymap)

    asyncio.run(run())


def test_einstellungen_ohne_sprachtab_und_namenssprache_bleibt(isolated_settings: Path) -> None:
    _schreibe(isolated_settings, {"language": "de", "keymap_style": "classic"})

    async def run() -> None:
        app = CodenameApp()
        async with app.run_test(size=(150, 45)) as pilot:
            await pilot.press("s")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, CodenameSettingsScreen)
            assert not screen.query("#settings-language")
            screen.query_one("#set-keymap-style", Select).value = "function_keys"
            screen.query_one("#set-keymap-vim", Checkbox).value = True
            await pilot.pause()
            await pilot.press("ctrl+s")
            await pilot.pause()
            gespeichert = json.loads(isolated_settings.read_text(encoding="utf-8"))
            assert gespeichert["keymap_style"] == "function_keys"
            assert gespeichert["keymap_vim"] is True
            assert gespeichert["language"] == "de"
            # Wiederoeffnen zeigt die gespeicherten Werte, nicht die Vorgabe.
            await pilot.press("s")
            await pilot.pause()
            assert app.screen.query_one("#set-keymap-style", Select).value == "function_keys"
            assert app.screen.query_one("#set-keymap-vim", Checkbox).value is True

    asyncio.run(run())


def test_speichern_behaelt_unbekannte_schluessel(isolated_settings: Path) -> None:
    """keymap_custom kommt nur von Hand in die Datei - kein Speichern darf es loeschen."""
    _schreibe(isolated_settings, {"keymap_custom": {"regenerate": ["x"]}})

    async def run() -> None:
        app = CodenameApp()
        async with app.run_test(size=(150, 45)) as pilot:
            await pilot.press("f")  # Favorit -> _save_settings
            await pilot.pause()
            gespeichert = json.loads(isolated_settings.read_text(encoding="utf-8"))
            assert gespeichert["keymap_custom"] == {"regenerate": ["x"]}
            assert gespeichert["favorites"]

    asyncio.run(run())


def test_vim_bindet_j_an_die_tabelle_und_meldet_l(isolated_settings: Path) -> None:
    _schreibe(isolated_settings, {"keymap_style": "classic", "keymap_vim": True})

    async def run() -> None:
        app = CodenameApp()
        async with app.run_test(size=(150, 45)) as pilot:
            await pilot.pause()
            tabelle = app.query_one("#suggestions", SuggestionsTable)
            assert "j" in tabelle._bindings.key_to_bindings
            assert any(p.action == "cycle_language" for p in app._keymap_problems)

    asyncio.run(run())
