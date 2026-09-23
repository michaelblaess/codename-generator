"""Themen-Mix in der echten TUI ("Mix with" im Panel), Settings isoliert."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from textual.widgets import Select, Static

from codename_generator import settings as settings_module
from codename_generator.tui import MIX_NONE, CodenameApp


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(settings_module, "_SETTINGS_DIR", tmp_path)
    monkeypatch.setattr(settings_module, "_SETTINGS_FILE", settings_file)
    return settings_file


def test_mix_kreuzt_speichert_und_faellt_zurueck(isolated_settings: Path) -> None:
    async def run() -> None:
        app = CodenameApp()
        async with app.run_test(size=(150, 45)) as pilot:
            app.mutation_percent = 0
            app._switch_theme("theme-whisky")
            await pilot.pause()
            vorher = [s.name for s in app.suggestions]

            app.query_one("#mix-select", Select).value = "constellations"
            await pilot.pause()
            whisky = {w.casefold() for w in app.generator.themes["whisky"].words}
            sterne = {w.casefold() for w in app.generator.themes["constellations"].words}
            recipes = app._recipes[app._theme_key()]
            assert len(recipes) == app.suggestion_count
            for r in recipes:
                assert r.anchor.casefold() in whisky and r.theme_word.casefold() in sterne
            assert "Whisky x Constellations" in str(app.query_one("#info", Static).content)
            gespeichert = json.loads(isolated_settings.read_text(encoding="utf-8"))
            assert gespeichert["mix_partner"] == "constellations"

            # Ohne Mix kommt der alte Stapel zurueck - eigener Cache-Schluessel.
            app.query_one("#mix-select", Select).value = MIX_NONE
            await pilot.pause()
            assert [s.name for s in app.suggestions] == vorher

            # Sternbilder sind englisch - auf Deutsch faellt der Mix weg.
            app.query_one("#mix-select", Select).value = "constellations"
            await pilot.pause()
            await app._apply_language("de")
            await pilot.pause()
            assert app._mix_partner == ""
            assert app.query_one("#mix-select", Select).value == MIX_NONE

    asyncio.run(run())
