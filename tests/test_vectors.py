"""Gemeinsame Testvektoren - dieselbe Datei prueft auch den TypeScript-Port.

Die Vektoren liegen in tests/vectors/core.json und werden per `npm run daten`
nach codename-generator.de kopiert. Weicht eine Implementierung ab, wird die
jeweilige Suite rot.
"""

from __future__ import annotations

import json
import random
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TypeVar

import pytest

from codename_generator.coinage import CoinModel, blend, coin_tokens, coin_word
from codename_generator.generator import (
    AnchorPosition,
    Generator,
    Pattern,
    Recipe,
    Suggestion,
    _slugify,
    anchor_modifier_patterns,
    anchor_theme_patterns,
    normalize_letters,
)
from codename_generator.grammar import inflect_attribute
from codename_generator.phonetic import mutate
from codename_generator.scoring import NameFilter, matches, name_syllables, sound_score
from codename_generator.wordlist import WordList

_T = TypeVar("_T")

_VECTORS: dict[str, Any] = json.loads(
    (Path(__file__).parent / "vectors" / "core.json").read_text(encoding="utf-8")
)


class ScriptedRandom(random.Random):
    """Zufall nach Drehbuch: jede Entscheidung kommt aus einer festen Indexfolge.

    Dieselbe Semantik steckt im TypeScript-Gegenstueck, sonst waeren die
    Vektoren nicht vergleichbar.
    """

    def __init__(self, script: Sequence[int]) -> None:
        super().__init__(0)
        self._script = list(script)
        self._position = 0

    def _next_index(self) -> int:
        if self._position >= len(self._script):
            raise AssertionError("Drehbuch zu kurz fuer diesen Vektor")
        value = self._script[self._position]
        self._position += 1
        return value

    def choice(self, seq: Sequence[_T]) -> _T:  # type: ignore[override]
        return seq[self._next_index() % len(seq)]

    def sample(self, population: Sequence[_T], k: int, *, counts: object = None) -> list[_T]:
        pool = list(population)
        return [pool.pop(self._next_index() % len(pool)) for _ in range(k)]


def _ids(cases: list[dict[str, Any]], key: str) -> list[str]:
    return [str(case.get("_note") or case[key]) for case in cases]


@pytest.mark.parametrize("case", _VECTORS["slugify"], ids=_ids(_VECTORS["slugify"], "input"))
def test_slugify(case: dict[str, Any]) -> None:
    assert _slugify(case["input"]) == case["expected"]


@pytest.mark.parametrize("case", _VECTORS["title"], ids=_ids(_VECTORS["title"], "input"))
def test_title(case: dict[str, Any]) -> None:
    assert case["input"].title() == case["expected"]


@pytest.mark.parametrize("case", _VECTORS["inflect"], ids=_ids(_VECTORS["inflect"], "word"))
def test_inflect(case: dict[str, Any]) -> None:
    result = inflect_attribute(case["word"], case["gender"], case["language"])
    assert result == case["expected"]


@pytest.mark.parametrize("case", _VECTORS["mutate"], ids=_ids(_VECTORS["mutate"], "word"))
def test_mutate(case: dict[str, Any]) -> None:
    rng = ScriptedRandom(case["script"])
    assert mutate(case["word"], rng, intensity=case.get("intensity", 1)) == case["expected"]


def _theme(raw: dict[str, Any]) -> WordList:
    return WordList(
        slug="vector",
        name="vector",
        description="",
        words=tuple(raw["words"]),
        patterns=tuple(raw.get("patterns", ())),
        mutate=raw.get("mutate", True),
        language=raw["language"],
        genders=tuple(raw.get("genders", ())),
    )


@pytest.mark.parametrize("case", _VECTORS["render"], ids=_ids(_VECTORS["render"], "_note"))
def test_render(case: dict[str, Any]) -> None:
    generator = Generator(themes={}, modifiers={}, rng=random.Random(0))
    raw = case["recipe"]
    recipe = Recipe(
        theme_word=raw["theme_word"],
        adjective=raw["adjective"],
        verb=raw["verb"],
        agent=raw["agent"],
        pattern_index=raw["pattern_index"],
        # Ohne Mutation - deren Zufall ist zwischen Python und JS verschieden.
        mutation_roll=1.0,
        mutation_seed=0,
        anchor=raw.get("anchor", ""),
    )
    suggestion = generator.render(
        recipe,
        _theme(case["theme"]),
        word_count=case["word_count"],
        mutation_chance=0.0,
        language=case["language"],
    )
    expected = case["expected"]
    assert suggestion.name == expected["name"]
    assert suggestion.slug == expected["slug"]
    assert suggestion.pattern.value == expected["pattern"]
    assert list(suggestion.source_words) == expected["sources"]
    assert suggestion.mutated is False


@pytest.mark.parametrize("case", _VECTORS["favorite"], ids=_ids(_VECTORS["favorite"], "_note"))
def test_favorite(case: dict[str, Any]) -> None:
    generator = Generator(themes={}, modifiers={}, rng=random.Random(0))
    stored = Suggestion(
        name="",
        slug="stored",
        pattern=Pattern(case["pattern"]),
        mutated=False,
        source_words=tuple(case["sources"]),
    )
    rendered = generator.render_favorite(stored, mutation_chance=0.0)
    assert rendered.name == case["expected"]["name"]
    assert rendered.slug == case["expected"]["slug"]
    assert rendered.mutated is False


@pytest.mark.parametrize(
    "case", _VECTORS["anchor_patterns"], ids=_ids(_VECTORS["anchor_patterns"], "_note")
)
def test_anchor_patterns(case: dict[str, Any]) -> None:
    position = AnchorPosition(case["position"])
    patterns = (
        anchor_modifier_patterns(case["language"], position)
        if case["kind"] == "modifier"
        else anchor_theme_patterns(position)
    )
    assert [p.value for p in patterns] == case["expected"]


def _index_ids(cases: list[dict[str, Any]], key: str) -> list[str]:
    return [f"{i}-{case.get('_note') or case[key]}" for i, case in enumerate(cases)]


@pytest.mark.parametrize("case", _VECTORS["coin"], ids=_index_ids(_VECTORS["coin"], "_note"))
def test_coin(case: dict[str, Any]) -> None:
    model = CoinModel.from_words(case["words"])
    assert coin_word(model, ScriptedRandom(case["script"])) == case["expected"]


@pytest.mark.parametrize(
    "case", _VECTORS["coin_tokens"], ids=_ids(_VECTORS["coin_tokens"], "_note")
)
def test_coin_tokens(case: dict[str, Any]) -> None:
    assert list(coin_tokens(case["words"])) == case["expected"]


@pytest.mark.parametrize("case", _VECTORS["blend"], ids=_index_ids(_VECTORS["blend"], "first"))
def test_blend(case: dict[str, Any]) -> None:
    assert blend(case["first"], case["second"]) == case["expected"]


@pytest.mark.parametrize(
    "case", _VECTORS["syllables"], ids=_index_ids(_VECTORS["syllables"], "name")
)
def test_syllables(case: dict[str, Any]) -> None:
    assert name_syllables(case["name"], case["language"]) == case["expected"]


@pytest.mark.parametrize("case", _VECTORS["score"], ids=_index_ids(_VECTORS["score"], "name"))
def test_score(case: dict[str, Any]) -> None:
    assert sound_score(case["name"], case["language"]) == case["expected"]


@pytest.mark.parametrize("case", _VECTORS["filter"], ids=_index_ids(_VECTORS["filter"], "name"))
def test_filter(case: dict[str, Any]) -> None:
    name_filter = NameFilter(**case["filter"])
    assert matches(case["name"], name_filter, case["language"]) is case["expected"]


@pytest.mark.parametrize("case", _VECTORS["letters"], ids=_index_ids(_VECTORS["letters"], "input"))
def test_letters(case: dict[str, Any]) -> None:
    assert normalize_letters(case["input"]) == case["expected"]


_LOADED = Generator.load(seed=0)


@pytest.mark.parametrize(
    "case", _VECTORS["tone_pool"], ids=_index_ids(_VECTORS["tone_pool"], "role")
)
def test_tone_pool(case: dict[str, Any]) -> None:
    pool = _LOADED._modifier_pool(case["language"], case["role"], case["tone"])
    assert list(pool) == case["expected"]


@pytest.mark.parametrize(
    "case", _VECTORS["acronym_patterns"], ids=_index_ids(_VECTORS["acronym_patterns"], "letters")
)
def test_acronym_patterns(case: dict[str, Any]) -> None:
    theme = _LOADED.acronym_theme(
        _LOADED.themes[case["theme"]], case["letters"], case["language"], case["tone"]
    )
    assert list(theme.patterns) == case["expected"]
