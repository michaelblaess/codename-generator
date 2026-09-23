"""Der Custom Seed in der echten TUI: Partner und Position ueber die Auswahlfelder.

Laeuft headless ueber Textuals Pilot. Die Settings landen in einem
temporaeren Ordner - der Test darf die echte settings.json nie anfassen.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from textual.widgets import Select

from codename_generator import settings as settings_module
from codename_generator.tui import SEED_PARTNER_MODIFIERS, CodenameApp


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(settings_module, "_SETTINGS_DIR", tmp_path)
    monkeypatch.setattr(settings_module, "_SETTINGS_FILE", settings_file)
    return settings_file


def test_seed_partner_and_position(isolated_settings: Path) -> None:
    async def run() -> None:
        app = CodenameApp()
        async with app.run_test(size=(140, 45)) as pilot:
            app._on_seed_entered("Sitemap")
            await pilot.pause()
            assert app._seed_mode
            # Mit Zusaetzen darf die Mutation das eigene Wort verbiegen - nur
            # die unveraenderten Namen muessen es woertlich tragen.
            plain = [s.name for s in app.suggestions if not s.mutated]
            assert plain
            assert all("Sitemap" in n for n in plain), plain

            app.query_one("#seed-partner-select", Select).value = "constellations"
            app.query_one("#seed-position-select", Select).value = "front"
            await pilot.pause()
            names = [s.name for s in app.suggestions]
            assert len(names) == app.suggestion_count
            assert all(n.startswith("Sitemap ") for n in names), names
            assert len(set(names)) == len(names)

            saved = json.loads(isolated_settings.read_text(encoding="utf-8"))
            assert saved["seed_partner"] == "constellations"
            assert saved["seed_position"] == "front"

            # Sternbilder sind englisch - auf Deutsch faellt der Partner zurueck.
            await app._apply_language("de")
            await pilot.pause()
            assert app._seed_partner == ""
            partner_select = app.query_one("#seed-partner-select", Select)
            assert partner_select.value == SEED_PARTNER_MODIFIERS
            plain = [s.name for s in app.suggestions if not s.mutated]
            assert all(n.startswith("Sitemap ") for n in plain), plain

    asyncio.run(run())


def test_seed_settings_survive_restart(isolated_settings: Path) -> None:
    isolated_settings.write_text(
        json.dumps(
            {"custom_seed": "Sitemap", "seed_partner": "greek-gods", "seed_position": "back"}
        ),
        encoding="utf-8",
    )

    async def run() -> None:
        app = CodenameApp()
        async with app.run_test(size=(140, 45)) as pilot:
            await pilot.pause()
            assert app.query_one("#seed-partner-select", Select).value == "greek-gods"
            assert app.query_one("#seed-position-select", Select).value == "back"
            app._on_seed_entered("Sitemap")
            await pilot.pause()
            assert all(s.name.endswith(" Sitemap") for s in app.suggestions)

    asyncio.run(run())
