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

from codename_generator.generator import Generator, Recipe, _slugify
from codename_generator.grammar import inflect_attribute
from codename_generator.phonetic import mutate
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
