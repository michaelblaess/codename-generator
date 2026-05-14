from __future__ import annotations

from codename_generator.generator import Generator, Pattern


def test_load_generator() -> None:
    gen = Generator.load(seed=0)
    assert "greek-gods" in gen.themes
    assert "adjectives" in gen.modifiers
    assert "verbs" in gen.modifiers


def test_suggest_count() -> None:
    gen = Generator.load(seed=1)
    suggestions = gen.suggest("flowers", count=10)
    assert len(suggestions) == 10
    slugs = {s.slug for s in suggestions}
    assert len(slugs) == 10


def test_suggest_deterministic_with_seed() -> None:
    a = Generator.load(seed=42).suggest("greek-gods", count=5, mutation_chance=0.5)
    b = Generator.load(seed=42).suggest("greek-gods", count=5, mutation_chance=0.5)
    assert [s.slug for s in a] == [s.slug for s in b]


def test_suggest_unknown_theme_raises() -> None:
    gen = Generator.load(seed=0)
    try:
        gen.suggest("does-not-exist")
    except KeyError:
        return
    raise AssertionError("expected KeyError")


def test_suggest_no_mutation_keeps_originals_except_theme_only() -> None:
    """Mit mutation_chance=0 sind nur Modifier-Patterns unmutiert.

    Pattern.THEME_ONLY erzwingt immer Mutation, da das Quellwort sonst
    unveraendert als Vorschlag erscheinen wuerde.
    """
    gen = Generator.load(seed=7)
    suggestions = gen.suggest("greek-gods", count=20, mutation_chance=0.0)
    for s in suggestions:
        if s.pattern is Pattern.THEME_ONLY:
            assert s.mutated, f"THEME_ONLY must always be mutated: {s}"
        else:
            assert not s.mutated, f"non-THEME_ONLY must not be mutated at 0%: {s}"


def test_pattern_enum_covers_all_used() -> None:
    gen = Generator.load(seed=0)
    suggestions = gen.suggest("flowers", count=50, mutation_chance=0.0)
    patterns_used = {s.pattern for s in suggestions}
    assert patterns_used.issubset(set(Pattern))


def test_theme_only_never_returns_bare_source_word() -> None:
    """THEME_ONLY-Vorschlaege duerfen niemals identisch mit dem Quellwort sein."""
    gen = Generator.load(seed=123)
    theme_words = {w.lower() for w in gen.themes["racehorses"].words}
    suggestions = gen.suggest("racehorses", count=50, mutation_chance=0.0)
    for s in suggestions:
        if s.pattern is Pattern.THEME_ONLY:
            assert s.mutated, f"theme-only must be mutated: {s}"
            assert s.name.lower() not in theme_words, f"bare source word leaked: {s}"


def test_random_theme_exists_and_pools_words() -> None:
    gen = Generator.load(seed=0)
    assert "random" in gen.themes
    random_words = set(gen.themes["random"].words)
    other_words: set[str] = set()
    for slug, theme in gen.themes.items():
        if slug != "random":
            other_words.update(theme.words)
    assert random_words == other_words
