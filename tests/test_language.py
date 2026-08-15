from __future__ import annotations

from codename_generator.generator import Generator, Pattern, _slugify, effective_language
from codename_generator.wordlist import available_languages, load_modifiers, load_themes

_GERMAN_THEME = "tierwelt"


def test_slugify_writes_out_umlauts() -> None:
    """Umlaute gehoeren ausgeschrieben in den Slug, nicht entfernt."""
    assert _slugify("Grüner Blitz") == "gruener-blitz"
    assert _slugify("Wüstenfuchs") == "wuestenfuchs"
    assert _slugify("Weiße Möwe") == "weisse-moewe"


def test_slugify_strips_accents() -> None:
    assert _slugify("Volupté") == "volupte"


def test_german_modifier_pools_exist() -> None:
    assert "de" in available_languages()
    pools = load_modifiers("de")
    for role in ("adjectives", "verbs", "agents"):
        assert pools[role].words, f"empty german pool: {role}"


def test_unknown_language_falls_back_to_default_pools() -> None:
    assert load_modifiers("xx")["adjectives"].words == load_modifiers("en")["adjectives"].words


def test_german_themes_declare_language_and_genders() -> None:
    themes = load_themes()
    german = [t for t in themes.values() if t.language == "de"]
    assert german, "expected at least one german theme"
    for theme in german:
        assert len(theme.genders) == len(theme.words)
        assert all(g in ("m", "f", "n", "p") for g in theme.genders)


def test_german_adjectives_are_inflected_by_gender() -> None:
    """Ein deutsches Theme beugt den vorangestellten Modifier nach dem Genus."""
    gen = Generator.load(seed=7)
    theme = gen.themes[_GERMAN_THEME]
    suggestions = gen.suggest(_GERMAN_THEME, count=40, mutation_chance=0.0, word_count=2)
    endings = {"m": "er", "f": "e", "n": "es", "p": "e"}
    checked = 0
    for s in suggestions:
        if s.pattern not in (Pattern.ADJ_THEME, Pattern.VERB_THEME):
            continue
        modifier = s.name.split()[0]
        gender = theme.gender_of(s.source_words[0])
        assert modifier.lower().endswith(endings[gender]), f"{s.name} ({gender})"
        checked += 1
    assert checked, "expected inflected suggestions in the sample"


def test_german_never_uses_trailing_participle() -> None:
    """ "Falke Jagend" ist keine deutsche Wortstellung - THEME_VERB faellt weg."""
    gen = Generator.load(seed=11)
    suggestions = gen.suggest(_GERMAN_THEME, count=60, mutation_chance=0.0, word_count=2)
    assert suggestions
    assert all(s.pattern is not Pattern.THEME_VERB for s in suggestions)


def test_german_three_word_names_put_both_modifiers_first() -> None:
    gen = Generator.load(seed=5)
    suggestions = gen.suggest(_GERMAN_THEME, count=20, mutation_chance=0.0, word_count=3)
    assert suggestions
    for s in suggestions:
        assert s.pattern is Pattern.ADJ_VERB_THEME
        # Das Theme-Wort steht hinten.
        assert s.name.split()[-1].lower() == s.source_words[0].lower()


def test_random_themes_do_not_mix_languages() -> None:
    """Jedes Random-Theme zieht nur aus Themes seiner eigenen Sprache.

    Geprueft wird die Herkunft, nicht die Schreibweise: ein Wort wie "Otter"
    steht in beiden Sprachen und darf in beiden Pools auftauchen.
    """
    gen = Generator.load(seed=0)
    by_language = {
        language: {
            w
            for slug, t in gen.themes.items()
            if t.language in (language, "neutral") and not slug.startswith("random")
            for w in t.words
        }
        for language in ("en", "de")
    }
    assert set(gen.themes["random"].words) == by_language["en"]
    assert set(gen.themes["random-de"].words) == by_language["de"]
    # Das deutsche Random-Theme behaelt die Genus-Information.
    assert len(gen.themes["random-de"].genders) == len(gen.themes["random-de"].words)


def test_neutral_themes_follow_the_chosen_language() -> None:
    """Ein Eigennamen-Theme zieht die Modifier der gewaehlten Sprache."""
    gen = Generator.load(seed=13)
    german = set(gen.modifiers["de"]["adjectives"].words)
    english = set(gen.modifiers["en"]["adjectives"].words)
    for recipe in gen.generate_recipes("racehorses", count=15, language="de"):
        assert recipe.adjective in german
    for recipe in gen.generate_recipes("racehorses", count=15, language="en"):
        assert recipe.adjective in english


def test_neutral_theme_is_inflected_when_german_is_active() -> None:
    """Ohne Genus-Marker gilt das Maskulinum - "Stiller Secretariat"."""
    gen = Generator.load(seed=13)
    suggestions = gen.suggest("swatch", count=30, mutation_chance=0.0, word_count=2, language="de")
    front = [s for s in suggestions if s.pattern in (Pattern.ADJ_THEME, Pattern.VERB_THEME)]
    assert front
    for s in front:
        assert s.name.split()[0].endswith(("er", "es", "e"))


def test_language_does_not_override_a_bound_theme() -> None:
    """Ein deutsches Theme bleibt deutsch, auch wenn Englisch gewaehlt ist."""
    gen = Generator.load(seed=13)
    german = set(gen.modifiers["de"]["adjectives"].words)
    for recipe in gen.generate_recipes(_GERMAN_THEME, count=15, language="en"):
        assert recipe.adjective in german


def test_effective_language_resolution() -> None:
    themes = load_themes()
    assert effective_language(themes["swatch"], "de") == "de"
    assert effective_language(themes["swatch"], None) == "en"
    assert effective_language(themes[_GERMAN_THEME], "en") == "de"
    assert effective_language(themes["animals"], "de") == "en"


def test_neutral_themes_are_declared() -> None:
    """Eigennamen-Themes sind als neutral markiert, Gattungswoerter nicht."""
    themes = load_themes()
    for slug in ("swatch", "racehorses", "whisky", "greek-gods", "mountains"):
        assert themes[slug].language == "neutral", slug
    for slug in ("animals", "flowers", "gemstones", "zodiac", "constellations"):
        assert themes[slug].language == "en", slug


def test_german_theme_uses_german_modifiers() -> None:
    gen = Generator.load(seed=2)
    german_adjectives = set(gen.modifiers["de"]["adjectives"].words)
    english_adjectives = set(gen.modifiers["en"]["adjectives"].words)
    recipes = gen.generate_recipes(_GERMAN_THEME, count=25)
    assert recipes
    for recipe in recipes:
        assert recipe.adjective in german_adjectives
        assert recipe.adjective not in english_adjectives
