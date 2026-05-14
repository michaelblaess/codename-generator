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


def test_zero_mutation_chance_produces_no_mutations() -> None:
    """Bei mutation_chance=0 darf nichts mutiert sein, auch kein THEME_ONLY.

    Der THEME_ONLY-Pattern faellt bei 0% komplett weg, weil er sonst sein
    eigenes Force-Mutation-Verhalten triggern wuerde.
    """
    gen = Generator.load(seed=7)
    suggestions = gen.suggest("greek-gods", count=20, mutation_chance=0.0)
    for s in suggestions:
        assert not s.mutated, f"no suggestion may be mutated at 0%: {s}"
        assert s.pattern is not Pattern.THEME_ONLY, (
            f"THEME_ONLY must not appear at 0%: {s}"
        )


def test_pattern_enum_covers_all_used() -> None:
    gen = Generator.load(seed=0)
    suggestions = gen.suggest("flowers", count=50, mutation_chance=0.0)
    patterns_used = {s.pattern for s in suggestions}
    assert patterns_used.issubset(set(Pattern))


def test_theme_only_never_returns_bare_source_word() -> None:
    """THEME_ONLY-Vorschlaege duerfen niemals identisch mit dem Quellwort sein."""
    gen = Generator.load(seed=123)
    theme_words = {w.lower() for w in gen.themes["racehorses"].words}
    # mutation_chance > 0 noetig, sonst kommt THEME_ONLY gar nicht vor
    suggestions = gen.suggest("racehorses", count=50, mutation_chance=0.3)
    for s in suggestions:
        if s.pattern is Pattern.THEME_ONLY:
            assert s.mutated, f"theme-only must be mutated: {s}"
            assert s.name.lower() not in theme_words, f"bare source word leaked: {s}"


def test_each_theme_word_appears_at_most_once() -> None:
    """Quellwoerter sind dedupliziert - keine Mehrfach-Mutationen desselben Worts."""
    gen = Generator.load(seed=42)
    suggestions = gen.suggest("racehorses", count=30, mutation_chance=0.6)
    theme_words = [s.source_words[0].lower() for s in suggestions]
    assert len(theme_words) == len(set(theme_words)), (
        f"duplicate theme words: {theme_words}"
    )


def test_source_words_normalized_theme_first() -> None:
    """source_words[0] muss immer das Theme-Wort sein, unabhaengig vom Pattern."""
    gen = Generator.load(seed=11)
    theme_word_set = {w.lower() for w in gen.themes["flowers"].words}
    suggestions = gen.suggest("flowers", count=30, mutation_chance=0.0)
    for s in suggestions:
        assert s.source_words[0].lower() in theme_word_set, (
            f"source_words[0] is not from theme: {s}"
        )


def test_random_theme_exists_and_pools_words() -> None:
    gen = Generator.load(seed=0)
    assert "random" in gen.themes
    random_words = set(gen.themes["random"].words)
    other_words: set[str] = set()
    for slug, theme in gen.themes.items():
        if slug != "random":
            other_words.update(theme.words)
    assert random_words == other_words
