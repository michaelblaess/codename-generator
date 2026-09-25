"""Stapel bauen, darstellen, Alliteration und der Austausch der Favoriten."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from codename_generator import cli
from codename_generator import settings as settings_module
from codename_generator.favorites import merge_favorites, parse_favorites
from codename_generator.generator import (
    Generator,
    Method,
    Pattern,
    PresentOptions,
    StackRequest,
    Suggestion,
    same_initial,
)
from codename_generator.scoring import NameFilter, is_alliteration


@pytest.fixture
def gen() -> Generator:
    return Generator.load(seed=21)


def test_words_stack_equals_the_old_path() -> None:
    # Die Themenansicht laeuft jetzt ueber build_stack - die Zugfolge muss bleiben.
    old = Generator.load(seed=9).generate_recipes("animals", 15, "en")
    new_gen = Generator.load(seed=9)
    stack = new_gen.build_stack(StackRequest(theme=new_gen.themes["animals"], count=15))
    assert stack.recipes == old


def test_words_stack_with_partner_is_the_mix(gen: Generator) -> None:
    stack = gen.build_stack(
        StackRequest(theme=gen.themes["mountains"], count=10, partner=gen.themes["constellations"])
    )
    assert stack.theme.slug == "mix-mountains-constellations"
    assert all(r.anchor for r in stack.recipes)


@pytest.mark.parametrize("method", [Method.COINED, Method.BLEND, Method.ACRONYM])
def test_every_method_builds_a_stack(gen: Generator, method: Method) -> None:
    stack = gen.build_stack(
        StackRequest(theme=gen.themes["animals"], count=10, method=method, letters="sm")
    )
    assert stack.recipes
    assert stack.theme.mutate is False


def test_present_keeps_recipe_and_suggestion_together(gen: Generator) -> None:
    theme = gen.themes["animals"]
    recipes = gen.generate_theme_recipes(theme, 40, "en")
    shown = gen.present(
        recipes,
        theme,
        PresentOptions(
            word_count=2,
            mutation_chance=0.0,
            language="en",
            name_filter=NameFilter(max_syllables=3),
            sort_by_score=True,
            limit=12,
        ),
    )
    assert 0 < len(shown) <= 12
    scores = [item.score for item in shown]
    assert scores == sorted(scores, reverse=True)
    for item in shown:
        again = gen.render(item.recipe, theme, 2, 0.0, "en")
        assert again.name == item.suggestion.name
        assert item.suggestion.name.count(" ") == 1


def test_present_without_options_keeps_order(gen: Generator) -> None:
    theme = gen.themes["animals"]
    recipes = gen.generate_theme_recipes(theme, 10, "en")
    shown = gen.present(recipes, theme, PresentOptions(mutation_chance=0.0))
    assert [item.recipe for item in shown] == recipes


def test_same_initial_falls_back_to_the_pool() -> None:
    assert same_initial(("silent", "swift", "bold"), "Sparrow") == ("silent", "swift")
    assert same_initial(("silent", "bold"), "Xerus") == ("silent", "bold")


def test_alliteration_is_drawn_not_only_filtered(gen: Generator) -> None:
    theme = gen.themes["animals"]
    recipes = gen.generate_theme_recipes(theme, 30, "en", alliterate=True)
    names = [gen.render(r, theme, 2, 0.0, "en").name for r in recipes]
    hits = sum(1 for name in names if is_alliteration(name))
    # Ohne den Schalter lag die Quote bei wenigen Prozent.
    assert hits >= 25, names


def _favorite(slug: str) -> Suggestion:
    return Suggestion(slug.title(), slug, Pattern.THEME_ONLY, False, (slug.title(),))


def test_parse_favorites_accepts_list_and_document() -> None:
    entry = {
        "name": "Silent Falcon",
        "slug": "silent-falcon",
        "pattern": "adj-theme",
        "mutated": False,
        "source_words": ["Falcon", "silent"],
    }
    broken = {"name": "x", "slug": "x", "pattern": "nope", "source_words": []}
    assert [f.slug for f in parse_favorites([entry, broken])] == ["silent-falcon"]
    assert [f.slug for f in parse_favorites({"favorites": [entry]})] == ["silent-falcon"]
    assert parse_favorites({"theme": "x"}) == []
    assert parse_favorites("nonsense") == []


def test_merge_favorites_skips_known_slugs() -> None:
    merged, added = merge_favorites(
        [_favorite("orion")], [_favorite("orion"), _favorite("vega"), _favorite("vega")]
    )
    assert [f.slug for f in merged] == ["orion", "vega"]
    assert added == 1


def _isolate_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(settings_module, "_SETTINGS_DIR", tmp_path)
    monkeypatch.setattr(settings_module, "_SETTINGS_FILE", settings_file)
    return settings_file


def _run(monkeypatch: pytest.MonkeyPatch, *args: str) -> int:
    monkeypatch.setattr(sys, "argv", ["codename", *args])
    return cli.main()


def test_cli_export_and_import_roundtrip(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    settings_file = _isolate_settings(monkeypatch, tmp_path)
    settings_file.write_text(
        json.dumps(
            {
                "theme": "gruvbox",
                "favorites": [
                    {
                        "name": "Orion",
                        "slug": "orion",
                        "pattern": "theme",
                        "mutated": False,
                        "source_words": ["Orion"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    export = tmp_path / "export.json"
    assert _run(monkeypatch, "--export-favorites", str(export)) == 0
    assert json.loads(export.read_text(encoding="utf-8"))["favorites"][0]["slug"] == "orion"

    # Ein Web-Export mit einem bekannten und einem neuen Eintrag.
    web = tmp_path / "web.json"
    web.write_text(
        json.dumps(
            {
                "favorites": [
                    {
                        "name": "Orion",
                        "slug": "orion",
                        "pattern": "theme",
                        "mutated": False,
                        "source_words": ["Orion"],
                    },
                    {
                        "name": "Silent Vega",
                        "slug": "silent-vega",
                        "pattern": "adj-theme",
                        "mutated": False,
                        "source_words": ["Vega", "silent"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    assert _run(monkeypatch, "--import-favorites", str(web)) == 0
    assert "1 new favorites imported, 1 already there" in capsys.readouterr().out
    stored = json.loads(settings_file.read_text(encoding="utf-8"))
    assert [f["slug"] for f in stored["favorites"]] == ["orion", "silent-vega"]
    # Andere Einstellungen bleiben stehen.
    assert stored["theme"] == "gruvbox"


def test_cli_import_rejects_empty_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _isolate_settings(monkeypatch, tmp_path)
    empty = tmp_path / "empty.json"
    empty.write_text("[]", encoding="utf-8")
    assert _run(monkeypatch, "--import-favorites", str(empty)) == 2
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    assert _run(monkeypatch, "--import-favorites", str(broken)) == 2


def test_cli_acronym_needs_letters(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _run(monkeypatch, "-t", "animals", "--method", "acronym") == 2


def test_cli_sort_prints_scores(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(monkeypatch, "-t", "animals", "--sort", "-n", "5", "--seed", "1") == 0
    lines = capsys.readouterr().out.strip().splitlines()
    scores = [int(line[5:8]) for line in lines]
    assert len(scores) == 5
    assert scores == sorted(scores, reverse=True)
