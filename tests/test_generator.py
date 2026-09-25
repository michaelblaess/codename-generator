from __future__ import annotations

import pytest

from codename_generator.generator import (
    CUSTOM_SEED_SLUG,
    PATTERN_WORD_COUNT,
    AnchorPosition,
    Generator,
    Pattern,
    Recipe,
    VariantKeep,
)
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
    assert "adjectives" in gen.modifiers["en"]
    assert "verbs" in gen.modifiers["en"]


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
    assert len(theme_words) == len(set(theme_words)), f"duplicate theme words: {theme_words}"


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


def test_seeded_recipes_use_seed_as_theme_word() -> None:
    """Alle Recipes haben den uebergebenen Seed als theme_word."""
    gen = Generator.load(seed=7)
    recipes = gen.generate_seeded_recipes("Sitemap", count=30)
    assert len(recipes) == 30
    for recipe in recipes:
        assert recipe.theme_word == "Sitemap"


def test_seeded_recipes_yield_distinct_combinations() -> None:
    """Trotz gleichem theme_word ist jedes Recipe einzigartig (adj/verb/pattern)."""
    gen = Generator.load(seed=7)
    recipes = gen.generate_seeded_recipes("Sitemap", count=30)
    keys = {(r.adjective.lower(), r.verb.lower(), r.pattern_index) for r in recipes}
    assert len(keys) == len(recipes), "expected all recipes to have distinct combos"


def test_seeded_render_produces_varied_names() -> None:
    """Die gerenderten Vorschlaege fuer einen Seed sind sichtbar verschieden."""
    gen = Generator.load(seed=7)
    seed = "Sitemap"
    theme = gen.seeded_theme(seed)
    recipes = gen.generate_seeded_recipes(seed, count=20)
    suggestions = [gen.render(r, theme, word_count=2, mutation_chance=0.0) for r in recipes]
    # Der Seed kommt in jedem Namen vor (case-insensitive).
    for s in suggestions:
        assert seed.lower() in s.name.lower(), f"seed missing in name: {s.name}"


@pytest.mark.parametrize("language", ["en", "de"])
@pytest.mark.parametrize("word_count", [2, 3])
def test_seeded_names_never_repeat(language: str, word_count: int) -> None:
    """Ein voller Stapel (40) zu einem eigenen Wort hat keinen Namen doppelt.

    Vorher wurde auf der ganzen Kombination dedupliziert, sichtbar ist aber nur
    ein Teil davon - "Silent Sitemap" kam dann zweimal.
    """
    for seed_value in range(20):
        gen = Generator.load(seed=seed_value)
        theme = gen.seeded_theme("Sitemap", language)
        recipes = gen.generate_seeded_recipes("Sitemap", count=40, language=language)
        names = [gen.render(r, theme, word_count, 0.0, language).name for r in recipes]
        assert len(recipes) == 40
        assert len(set(names)) == len(names), f"seed {seed_value}: {sorted(names)}"


def test_seeded_theme_has_seed_word() -> None:
    gen = Generator.load(seed=0)
    theme = gen.seeded_theme("Sitemap")
    assert theme.slug == CUSTOM_SEED_SLUG
    assert theme.words == ("Sitemap",)
    assert theme.mutate is True


def test_agents_modifier_pool_loaded() -> None:
    """data/modifiers/agents.yaml wird als Pool 'agents' geladen."""
    gen = Generator.load(seed=0)
    assert "agents" in gen.modifiers["en"]
    agents = set(w.lower() for w in gen.modifiers["en"]["agents"].words)
    # Spot-Check: ein paar typische Agent-Nouns muessen drin sein.
    for word in ("runner", "generator", "inspector", "fixer", "crawler"):
        assert word in agents, f"expected '{word}' in agents pool"


def test_theme_agent_pattern_produces_theme_agent_combinations() -> None:
    """word_count=2 zieht mit nicht-trivialer Wahrscheinlichkeit THEME_AGENT."""
    gen = Generator.load(seed=3)
    seed = "Sitemap"
    theme = gen.seeded_theme(seed)
    recipes = gen.generate_seeded_recipes(seed, count=80)
    suggestions = [gen.render(r, theme, word_count=2, mutation_chance=0.0) for r in recipes]
    agent_suggestions = [s for s in suggestions if s.pattern is Pattern.THEME_AGENT]
    assert agent_suggestions, "expected at least one theme-agent suggestion in 80 draws"
    # Beispiel-Check: ein Agent-Vorschlag hat die Form "Sitemap <Agent>".
    sample = agent_suggestions[0]
    parts = sample.name.split()
    assert len(parts) == 2
    assert parts[0].lower() == seed.lower()


def test_theme_agent_falls_back_to_verb_when_agent_pool_missing() -> None:
    """Ohne agents-Pool fallback auf VERB - kein leerer Wortteil im Namen."""
    gen = Generator.load(seed=3)
    # agents-Pool gezielt entfernen.
    gen.modifiers["en"].pop("agents", None)
    seed = "Sitemap"
    theme = gen.seeded_theme(seed)
    recipes = gen.generate_seeded_recipes(seed, count=30)
    suggestions = [gen.render(r, theme, word_count=2, mutation_chance=0.0) for r in recipes]
    for s in suggestions:
        # Kein Namen darf einen doppelten Whitespace haben oder mit einem Space enden.
        assert "  " not in s.name, f"double space in: {s.name!r}"
        assert not s.name.endswith(" "), f"trailing space in: {s.name!r}"
        assert s.slug.strip("-") == s.slug, f"slug has leading/trailing dash: {s.slug!r}"


def test_random_theme_exists_and_pools_words() -> None:
    """Das Random-Theme poolt genau die Woerter SEINER Sprache."""
    gen = Generator.load(seed=0)
    assert "random" in gen.themes
    random_words = set(gen.themes["random"].words)
    other_words: set[str] = set()
    for slug, theme in gen.themes.items():
        if not slug.startswith("random") and theme.language in ("en", "neutral"):
            other_words.update(theme.words)
    assert random_words == other_words


@pytest.mark.parametrize("position", list(AnchorPosition))
def test_anchored_names_follow_position_and_never_repeat(position: AnchorPosition) -> None:
    """Eigenes Wort plus Partner-Thema: Stellung wie gewaehlt, kein Name doppelt."""
    for seed_value in range(10):
        gen = Generator.load(seed=seed_value)
        partner = gen.themes["constellations"]
        theme = gen.anchored_theme("Sitemap", partner, "en", position)
        recipes = gen.generate_anchored_recipes("Sitemap", partner, 40, position)
        names = [gen.render(r, theme, 3, 0.0, "en").name for r in recipes]
        assert len(names) == 40
        assert len(set(names)) == 40
        for name in names:
            assert name.count("Sitemap") == 1, name
            if position == AnchorPosition.FRONT:
                assert name.startswith("Sitemap "), name
            if position == AnchorPosition.BACK:
                assert name.endswith(" Sitemap"), name


def test_anchored_skips_partner_word_equal_to_anchor() -> None:
    """Kein "Orion Orion" - das gleiche Wort im Partner-Thema faellt weg."""
    gen = Generator.load(seed=1)
    partner = WordList(slug="p", name="p", description="", words=("Orion", "Lyra", "Vega"))
    recipes = gen.generate_anchored_recipes("orion", partner, 10)
    assert sorted(r.theme_word for r in recipes) == ["Lyra", "Vega"]


@pytest.mark.parametrize("language", ["en", "de"])
def test_seeded_position_puts_word_where_asked(language: str) -> None:
    """Eigenes Wort mit Zusaetzen: vorn heisst "Sitemap ...", hinten "... Sitemap"."""
    gen = Generator.load(seed=3)
    for position in (AnchorPosition.FRONT, AnchorPosition.BACK):
        theme = gen.seeded_theme("Sitemap", language, position)
        recipes = gen.generate_seeded_recipes("Sitemap", 30, language, position)
        names = [gen.render(r, theme, 3, 0.0, language).name for r in recipes]
        assert len(set(names)) == len(names) == 30
        for name in names:
            if position == AnchorPosition.FRONT:
                assert name.startswith("Sitemap "), name
            else:
                assert name.endswith(" Sitemap"), name


def _base(gen: Generator, slug: str, language: str) -> Recipe:
    return gen.generate_recipes(slug, count=1, language=language)[0]


@pytest.mark.parametrize("language", ["en", "de"])
@pytest.mark.parametrize("word_count", [2, 3])
def test_variant_keep_word(language: str, word_count: int) -> None:
    """Wort halten: jedes Ergebnis traegt das Theme-Wort, keins gleicht dem Ausgang."""
    slug = "animals" if language == "en" else "tierwelt"
    for seed_value in range(10):
        gen = Generator.load(seed=seed_value)
        theme = gen.themes[slug]
        base = _base(gen, slug, language)
        original = gen.render(base, theme, word_count, 0.0, language).name
        recipes = gen.generate_variant_recipes(base, theme, VariantKeep.WORD, 30, language)
        names = [gen.render(r, theme, word_count, 0.0, language).name for r in recipes]
        assert len(names) == 30
        assert len(set(names)) == 30
        assert original not in names
        assert all(r.theme_word == base.theme_word for r in recipes)


def test_variant_keep_modifier_inflects_per_gender() -> None:
    """Zusatz halten auf Deutsch: derselbe Zusatz, gebeugt nach dem neuen Wort."""
    gen = Generator.load(seed=2)
    theme = gen.themes["tierwelt"]
    base = Recipe(
        theme_word="Falke",
        adjective="still",
        verb="jagend",
        agent="",
        pattern_index=0,
        mutation_roll=1.0,
        mutation_seed=0,
    )
    assert gen.render(base, theme, 2, 0.0, "de").name == "Stiller Falke"
    recipes = gen.generate_variant_recipes(base, theme, VariantKeep.MODIFIER, 40, "de")
    suggestions = [gen.render(r, theme, 2, 0.0, "de") for r in recipes]
    assert len(suggestions) == 40
    assert "Falke" not in [r.theme_word for r in recipes]
    for s, r in zip(suggestions, recipes, strict=True):
        ending = {"m": "Stiller", "f": "Stille", "n": "Stilles", "p": "Stille", "": "Stiller"}
        assert s.name == f"{ending[theme.gender_of(r.theme_word)]} {r.theme_word}", s.name


def test_variant_keep_modifier_keeps_anchor() -> None:
    """Zusatz halten bei einem Anker-Treffer: das eigene Wort bleibt, der Partner wechselt."""
    gen = Generator.load(seed=5)
    partner = gen.themes["greek-gods"]
    theme = gen.anchored_theme("Sitemap", partner, "en", AnchorPosition.FRONT)
    base = gen.generate_anchored_recipes("Sitemap", partner, 1, AnchorPosition.FRONT)[0]
    recipes = gen.generate_variant_recipes(base, theme, VariantKeep.MODIFIER, 20, "en")
    names = [gen.render(r, theme, 2, 0.0, "en").name for r in recipes]
    assert len(set(names)) == 20
    assert all(n.startswith("Sitemap ") for n in names)


def test_variant_on_single_word_theme_is_empty() -> None:
    """Power words kennen nur ein Wort pro Name - Wort halten hat nichts zu variieren."""
    gen = Generator.load(seed=1)
    theme = gen.themes["power-words"]
    base = _base(gen, "power-words", "en")
    assert gen.generate_variant_recipes(base, theme, VariantKeep.WORD, 20, "en") == []


def test_variant_keep_word_on_anchor_is_empty() -> None:
    """Wort halten bei "Sitemap Selene" wuerde den Anker verlieren - dann lieber nichts."""
    gen = Generator.load(seed=5)
    partner = gen.themes["greek-gods"]
    theme = gen.anchored_theme("Sitemap", partner, "en")
    base = gen.generate_anchored_recipes("Sitemap", partner, 1)[0]
    assert gen.generate_variant_recipes(base, theme, VariantKeep.WORD, 20, "en") == []


@pytest.mark.parametrize(
    ("first", "second", "language"),
    [("mountains", "constellations", "en"), ("tierwelt", "greek-gods", "de")],
)
def test_crossed_themes_use_each_word_once(first: str, second: str, language: str) -> None:
    """Themen-Mix: je ein Wort aus beiden Themes, keins doppelt, nie dasselbe zweimal."""
    for seed_value in range(10):
        gen = Generator.load(seed=seed_value)
        a, b = gen.themes[first], gen.themes[second]
        theme = gen.crossed_theme(a, b, language)
        recipes = gen.generate_crossed_recipes(a, b, 40)
        names = [gen.render(r, theme, 3, 0.0, language).name for r in recipes]
        assert len(names) == 40
        assert len(set(names)) == 40
        assert len({r.anchor for r in recipes}) == 40
        assert len({r.theme_word for r in recipes}) == 40
        for r, name in zip(recipes, names, strict=True):
            assert r.anchor in a.words and r.theme_word in b.words
            beide = {
                f"{r.anchor} {r.theme_word}".casefold(),
                f"{r.theme_word} {r.anchor}".casefold(),
            }
            assert name.casefold() in beide, name


def test_crossed_theme_never_pairs_a_word_with_itself() -> None:
    gen = Generator.load(seed=2)
    a = WordList(slug="a", name="A", description="", words=("Orion", "Lyra"))
    b = WordList(slug="b", name="B", description="", words=("Orion", "Vega"))
    recipes = gen.generate_crossed_recipes(a, b, 10)
    assert all(r.anchor != r.theme_word for r in recipes)
    assert len(recipes) == 2


def test_crossed_variant_keeps_first_word() -> None:
    """Zusatz halten auf einem Mix-Treffer behaelt das Wort aus dem ersten Theme."""
    gen = Generator.load(seed=4)
    a, b = gen.themes["mountains"], gen.themes["constellations"]
    theme = gen.crossed_theme(a, b, "en")
    base = gen.generate_crossed_recipes(a, b, 1)[0]
    recipes = gen.generate_variant_recipes(base, theme, VariantKeep.MODIFIER, 20, "en")
    assert len(recipes) == 20
    assert all(r.anchor == base.anchor and r.theme_word != base.theme_word for r in recipes)
