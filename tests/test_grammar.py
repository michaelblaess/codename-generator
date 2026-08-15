from __future__ import annotations

import pytest

from codename_generator.grammar import inflect_attribute


@pytest.mark.parametrize(
    ("word", "gender", "expected"),
    [
        ("still", "m", "stiller"),
        ("still", "f", "stille"),
        ("still", "n", "stilles"),
        ("still", "p", "stille"),
        # Stamm auf -el verliert das e: dunkel -> dunkler, nicht dunkeler.
        ("dunkel", "m", "dunkler"),
        ("edel", "n", "edles"),
        # Stamm, der schon auf e endet, bekommt nur den Rest der Endung.
        ("leise", "m", "leiser"),
        ("leise", "f", "leise"),
        ("leise", "n", "leises"),
        # Ohne Marker gilt Maskulinum.
        ("jagend", "", "jagender"),
    ],
)
def test_german_inflection(word: str, gender: str, expected: str) -> None:
    assert inflect_attribute(word, gender, "de") == expected


def test_english_is_left_alone() -> None:
    assert inflect_attribute("swift", "m", "en") == "swift"


def test_unknown_language_is_left_alone() -> None:
    assert inflect_attribute("rapide", "f", "fr") == "rapide"


def test_empty_word_stays_empty() -> None:
    assert inflect_attribute("", "m", "de") == ""
