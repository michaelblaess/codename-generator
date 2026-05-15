from __future__ import annotations

from codename_generator.generator import PATTERN_WORD_COUNT, Generator, Pattern
from codename_generator.wordlist import WordList


def test_word_count_one_yields_only_single_component() -> None:
    gen = Generator.load(seed=3)
    suggestions = gen.suggest("greek-gods", count=20, mutation_chance=0.6, word_count=1)
    assert suggestions
    for s in suggestions:
        assert PATTERN_WORD_COUNT[s.pattern] == 1, f"word_count=1 must be 1 word: {s}"


def test_word_count_two_yields_exactly_two_components() -> None:
    """word_count=2 -> ausschliesslich 2-Komponenten-Namen, keine 1- oder 3-Wort."""
    gen = Generator.load(seed=3)
    suggestions = gen.suggest("flowers", count=30, mutation_chance=0.5, word_count=2)
    assert suggestions
    for s in suggestions:
        assert PATTERN_WORD_COUNT[s.pattern] == 2, f"expected exactly 2 words: {s}"


def test_word_count_three_yields_exactly_three_components() -> None:
    """word_count=3 -> ausschliesslich 3-Wort-Namen (adj-theme-verb)."""
    gen = Generator.load(seed=3)
    suggestions = gen.suggest("flowers", count=30, mutation_chance=0.5, word_count=3)
    assert suggestions
    for s in suggestions:
        assert PATTERN_WORD_COUNT[s.pattern] == 3, f"expected exactly 3 words: {s}"
        assert s.pattern is Pattern.ADJ_THEME_VERB


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
    """Bei mutation_chance=0 darf kein Vorschlag mutiert sein."""
    gen = Generator.load(seed=7)
    suggestions = gen.suggest("greek-gods", count=20, mutation_chance=0.0)
    assert suggestions
    assert all(not s.mutated for s in suggestions)


def test_pattern_enum_covers_all_used() -> None:
    gen = Generator.load(seed=0)
    suggestions = gen.suggest("flowers", count=50, mutation_chance=0.0)
    patterns_used = {s.pattern for s in suggestions}
    assert patterns_used.issubset(set(Pattern))


def test_render_keeps_theme_word_stable_across_settings() -> None:
    """Dasselbe Recipe behaelt sein Theme-Wort bei jeder Mutation/Wortzahl."""
    gen = Generator.load(seed=5)
    recipes = gen.generate_recipes("greek-gods", count=10)
    theme = gen.themes["greek-gods"]
    for recipe in recipes:
        s1 = gen.render(recipe, theme, word_count=1, mutation_chance=0.0)
        s2 = gen.render(recipe, theme, word_count=2, mutation_chance=0.5)
        s3 = gen.render(recipe, theme, word_count=3, mutation_chance=1.0)
        assert s1.source_words[0] == recipe.theme_word
        assert s2.source_words[0] == recipe.theme_word
        assert s3.source_words[0] == recipe.theme_word
        assert PATTERN_WORD_COUNT[s1.pattern] == 1
        assert PATTERN_WORD_COUNT[s2.pattern] == 2
        assert PATTERN_WORD_COUNT[s3.pattern] == 3


def test_render_is_deterministic() -> None:
    """Gleiches Recipe + gleiche Parameter -> identische Suggestion."""
    gen = Generator.load(seed=5)
    recipes = gen.generate_recipes("flowers", count=5)
    theme = gen.themes["flowers"]
    for recipe in recipes:
        first = gen.render(recipe, theme, word_count=2, mutation_chance=1.0)
        second = gen.render(recipe, theme, word_count=2, mutation_chance=1.0)
        assert first == second


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


def test_evocative_and_power_words_default_to_zero_mutation() -> None:
    """Beide Themes erlauben Mutation, starten aber per Default bei 0%."""
    gen = Generator.load(seed=4)
    for slug in ("evocative", "power-words"):
        theme = gen.themes[slug]
        assert theme.mutate is True, f"{slug} should allow mutation"
        assert theme.default_mutation == 0, f"{slug} default_mutation should be 0"


def test_power_words_emits_clean_single_words() -> None:
    """power-words liefert bei 0% Mutation nackte, unmutierte Einzelwoerter."""
    gen = Generator.load(seed=4)
    theme_words = set(gen.themes["power-words"].words)
    suggestions = gen.suggest("power-words", count=20, mutation_chance=0.0)
    assert suggestions
    for s in suggestions:
        assert s.pattern is Pattern.THEME_ONLY
        assert not s.mutated
        assert s.name in theme_words, f"clean theme word expected: {s}"


def test_mutate_false_disables_mutation() -> None:
    """Ein Theme mit mutate=False mutiert nie, auch bei mutation_chance=1.0."""
    gen = Generator.load(seed=4)
    gen.themes["_mutate_test"] = WordList(
        slug="_mutate_test",
        name="Test",
        description="",
        words=("Pegasus", "Apollo", "Hermes", "Cerberus", "Hydra"),
        mutate=False,
    )
    suggestions = gen.suggest("_mutate_test", count=15, mutation_chance=1.0)
    assert suggestions
    assert all(not s.mutated for s in suggestions)


def test_theme_pattern_override_restricts_pool() -> None:
    """evocative deklariert patterns=[adj-theme] - nur dieses Pattern kommt vor."""
    gen = Generator.load(seed=4)
    # word_count wird ignoriert, weil das Theme eigene patterns deklariert.
    suggestions = gen.suggest("evocative", count=30, mutation_chance=0.5, word_count=1)
    assert suggestions
    assert all(s.pattern is Pattern.ADJ_THEME for s in suggestions)


def test_theme_modifier_override_uses_own_verbs() -> None:
    """dev nutzt eigene Verb-Liste fuer verb-basierte Patterns."""
    gen = Generator.load(seed=4)
    dev_verbs = {v.lower() for v in gen.themes["dev"].verbs}
    assert dev_verbs
    suggestions = gen.suggest("dev", count=40, mutation_chance=0.0)
    verb_patterns = (Pattern.VERB_THEME, Pattern.THEME_VERB)
    for s in suggestions:
        if s.pattern in verb_patterns:
            modifier = s.source_words[1].lower()
            assert modifier in dev_verbs, f"dev verb expected: {s}"


def test_random_theme_exists_and_pools_words() -> None:
    gen = Generator.load(seed=0)
    assert "random" in gen.themes
    random_words = set(gen.themes["random"].words)
    other_words: set[str] = set()
    for slug, theme in gen.themes.items():
        if slug != "random":
            other_words.update(theme.words)
    assert random_words == other_words
