from __future__ import annotations

from codename_generator.wordlist import load_modifiers, load_themes


def test_themes_loaded() -> None:
    themes = load_themes()
    assert len(themes) >= 5
    for theme in themes.values():
        assert theme.words
        assert all(isinstance(w, str) and w for w in theme.words)


def test_modifiers_loaded() -> None:
    mods = load_modifiers()
    assert "adjectives" in mods
    assert "verbs" in mods
    assert len(mods["adjectives"].words) > 20
    assert len(mods["verbs"].words) > 20
