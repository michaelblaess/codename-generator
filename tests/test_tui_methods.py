"""Methodenleiste der TUI: Methode, Akronym, Ton, Filter, Sortierung - Settings isoliert."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from textual.widgets import Checkbox, DataTable, Input, ListView, RichLog, Select, Static

from codename_generator import settings as settings_module
from codename_generator.scoring import is_alliteration, name_syllables
from codename_generator.tui import CodenameApp


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(settings_module, "_SETTINGS_DIR", tmp_path)
    monkeypatch.setattr(settings_module, "_SETTINGS_FILE", settings_file)
    return settings_file


def _log_text(app: CodenameApp) -> str:
    return "\n".join(line.text for line in app.query_one("#log", RichLog).lines)


def test_start_does_not_visit_favorites() -> None:
    async def run() -> None:
        app = CodenameApp()
        async with app.run_test(size=(150, 45)) as pilot:
            await pilot.pause()
            await pilot.pause()
            assert "favorites" not in _log_text(app)
            assert app.query_one("#theme-list", ListView).index == 2
            assert not app._favorites_mode

    asyncio.run(run())


def test_seed_entry_marks_the_seed_in_the_list() -> None:
    async def run() -> None:
        app = CodenameApp()
        async with app.run_test(size=(150, 45)) as pilot:
            app._on_seed_entered("Sitemap")
            await pilot.pause()
            assert app.query_one("#theme-list", ListView).index == 1
            assert app._seed_mode

    asyncio.run(run())


def test_method_bar_fits_at_150_columns() -> None:
    async def run() -> None:
        app = CodenameApp()
        async with app.run_test(size=(150, 45)) as pilot:
            await pilot.pause()
            sort = app.query_one("#sort-check", Checkbox)
            assert sort.region.width > 0
            assert sort.region.right <= 150

    asyncio.run(run())


def test_coined_and_acronym_from_the_bar(isolated_settings: Path) -> None:
    async def run() -> None:
        app = CodenameApp()
        async with app.run_test(size=(150, 45)) as pilot:
            app._switch_theme("theme-animals")
            await pilot.pause()
            app.query_one("#method-select", Select).value = "coined"
            await pilot.pause()
            assert "(coined)" in str(app.query_one("#info", Static).content)
            animals = {w.lower() for w in app.generator.themes["animals"].words}
            words = {r.theme_word.lower() for r in app._shown_recipes}
            assert words
            assert words.isdisjoint(animals)

            app.query_one("#method-select", Select).value = "acronym"
            await pilot.pause()
            letters = app.query_one("#letters-input", Input)
            assert letters.display
            placeholder = str(app.query_one("#suggestions", DataTable).get_row_at(0)[1])
            assert "three letters" in placeholder
            letters.value = "sm"
            await pilot.pause()
            assert app.suggestions
            for s in app.suggestions:
                assert "".join(p[0].lower() for p in s.name.split()) == "sm", s.name

            stored = json.loads(isolated_settings.read_text(encoding="utf-8"))
            assert stored["method"] == "acronym"
            assert stored["acronym_letters"] == "sm"

    asyncio.run(run())


def test_tone_filters_and_sort(isolated_settings: Path) -> None:
    async def run() -> None:
        app = CodenameApp()
        async with app.run_test(size=(150, 45)) as pilot:
            app.mutation_percent = 0
            app._switch_theme("theme-animals")
            await pilot.pause()

            app.query_one("#tone-select", Select).value = "calm"
            await pilot.pause()
            calm = set(app.generator._modifier_pool("en", "adjectives", "calm"))
            assert all(r.adjective in calm for r in app._shown_recipes)

            app.query_one("#initial-input", Input).value = "s"
            await pilot.pause()
            assert app.suggestions
            assert all(s.name.lower().startswith("s") for s in app.suggestions)

            app.query_one("#syllable-select", Select).value = "3"
            await pilot.pause()
            assert all(name_syllables(s.name, "en") <= 3 for s in app.suggestions)

            app.query_one("#initial-input", Input).value = ""
            app.query_one("#syllable-select", Select).value = "0"
            app.query_one("#alliteration-check", Checkbox).value = True
            await pilot.pause()
            assert len(app.suggestions) >= app.suggestion_count // 2
            assert all(is_alliteration(s.name) for s in app.suggestions)

            app.query_one("#alliteration-check", Checkbox).value = False
            app.query_one("#sort-check", Checkbox).value = True
            await pilot.pause()
            table = app.query_one("#suggestions", DataTable)
            scores = [int(str(table.get_row_at(i)[4])) for i in range(table.row_count)]
            assert scores == sorted(scores, reverse=True)

            # Variieren nimmt den angezeigten Treffer, nicht den gezogenen.
            table.move_cursor(row=3)
            await pilot.pause()
            base = app._shown_recipes[3]
            await pilot.press("w")
            await pilot.pause()
            assert app._variant_mode
            assert app._variant_base == base

            stored = json.loads(isolated_settings.read_text(encoding="utf-8"))
            assert stored["tone"] == "calm"
            assert stored["sort_by_score"] is True

    asyncio.run(run())


def test_settings_restore_the_bar(isolated_settings: Path) -> None:
    isolated_settings.write_text(
        json.dumps(
            {
                "method": "blend",
                "tone": "dark",
                "filter_initial": "Or",
                "filter_max_syllables": 4,
                "filter_alliteration": False,
                "sort_by_score": True,
                "acronym_letters": "abcd",
            }
        ),
        encoding="utf-8",
    )

    async def run() -> None:
        app = CodenameApp()
        async with app.run_test(size=(150, 45)) as pilot:
            await pilot.pause()
            assert app.query_one("#method-select", Select).value == "blend"
            assert app.query_one("#tone-select", Select).value == "dark"
            assert app.query_one("#initial-input", Input).value == "OR"
            assert app.query_one("#syllable-select", Select).value == "4"
            assert app.query_one("#sort-check", Checkbox).value is True
            assert not app.query_one("#letters-input", Input).display
            assert app._letters == "abc"

    asyncio.run(run())
