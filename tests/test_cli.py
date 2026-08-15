from __future__ import annotations

from codename_generator.cli import DEFAULT_MUTATION_CHANCE, _mutation_chance


def test_explicit_value_wins() -> None:
    assert _mutation_chance(0, 0.9) == 0.9


def test_theme_default_beats_global_default() -> None:
    assert _mutation_chance(0, None) == 0.0
    assert _mutation_chance(25, None) == 0.25


def test_falls_back_to_global_default() -> None:
    assert _mutation_chance(None, None) == DEFAULT_MUTATION_CHANCE
