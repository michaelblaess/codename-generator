"""Ton, Kunstwoerter, Kofferwoerter und Akronym im Generator."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from codename_generator.coinage import coin_tokens
from codename_generator.generator import Generator, Pattern
from codename_generator.wordlist import _wordlist_from_path


@pytest.fixture
def gen() -> Generator:
    return Generator.load(seed=11)


def test_tone_restricts_every_modifier(gen: Generator) -> None:
    dark = set(gen._modifier_pool("en", "adjectives", "dark"))
    verbs = set(gen._modifier_pool("en", "verbs", "dark"))
    agents = set(gen._modifier_pool("en", "agents", "dark"))
    recipes = gen.generate_recipes("animals", 30, "en", "dark")
    assert len(recipes) == 30
    for recipe in recipes:
        assert recipe.adjective in dark
        assert recipe.verb in verbs
        assert recipe.agent in agents


def test_no_tone_keeps_the_random_sequence() -> None:
    # Die Permalinks im Web haengen an der Zugfolge - ohne Ton darf sich nichts aendern.
    plain = Generator.load(seed=5).generate_recipes("animals", 20, "en")
    with_empty_tone = Generator.load(seed=5).generate_recipes("animals", 20, "en", "")
    assert plain == with_empty_tone


def test_tone_changes_the_names(gen: Generator) -> None:
    calm = {r.adjective for r in gen.generate_recipes("animals", 30, "en", "calm")}
    fierce = {r.adjective for r in gen.generate_recipes("animals", 30, "en", "fierce")}
    assert calm.isdisjoint(fierce - set(gen._modifier_pool("en", "adjectives", "calm")))
    assert calm <= set(gen._modifier_pool("en", "adjectives", "calm"))


def test_unknown_tone_falls_back_to_the_full_pool(gen: Generator) -> None:
    assert gen._modifier_pool("en", "adjectives", "sparkly") == gen._modifier_pool(
        "en", "adjectives"
    )


def test_theme_override_is_filtered_by_tone_or_kept(gen: Generator) -> None:
    theme = gen.themes["dev"]
    assert theme.verbs, "dev bringt eigene Verben mit - sonst prueft der Test nichts"
    # Keins der dev-Verben traegt einen Ton: die eigene Liste bleibt ganz.
    assert gen._theme_pool(theme, "en", "verbs", "dark") == theme.verbs
    # Mit markierten Woertern in der eigenen Liste greift der Ton.
    mixed = dataclasses.replace(theme, verbs=("hunt", "build", "run"))
    assert gen._theme_pool(mixed, "en", "verbs", "dark") == ("hunt",)
    assert gen._theme_pool(mixed, "en", "verbs", "swift") == ("run",)


def test_seeded_recipes_follow_the_tone(gen: Generator) -> None:
    swift = set(gen._modifier_pool("de", "adjectives", "swift"))
    recipes = gen.generate_seeded_recipes("Sitemap", 10, "de", tone="swift")
    assert recipes
    assert all(r.adjective in swift for r in recipes)


def test_tone_in_yaml_must_name_known_words(tmp_path: Path) -> None:
    bad = tmp_path / "adjectives.yaml"
    bad.write_text("name: X\nwords: [swift]\ntones:\n  dark: [gloomy]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown words"):
        _wordlist_from_path(bad)


def test_tone_in_yaml_must_be_known(tmp_path: Path) -> None:
    bad = tmp_path / "adjectives.yaml"
    bad.write_text("name: X\nwords: [swift]\ntones:\n  sparkly: [swift]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unknown tones"):
        _wordlist_from_path(bad)


def test_coined_words_are_new(gen: Generator) -> None:
    theme = gen.themes["constellations"]
    coined = gen.coined_theme(theme, 25)
    tokens = coin_tokens(theme.words)
    assert len(coined.words) == 25
    assert coined.mutate is False
    for word in coined.words:
        assert 4 <= len(word) <= 10
        assert not any(word.lower() in token for token in tokens), word
        assert word[0].isupper()


def test_coined_theme_works_with_modifiers(gen: Generator) -> None:
    coined = gen.coined_theme(gen.themes["greek-gods"], 10)
    recipes = gen.generate_theme_recipes(coined, 10, "en")
    names = [gen.render(r, coined, 2, 1.0, "en").name for r in recipes]
    assert len(names) == 10
    assert all(len(name.split()) == 2 for name in names)


def test_coined_with_partner_learns_from_both(gen: Generator) -> None:
    coined = gen.coined_theme(gen.themes["mountains"], 5, partner=gen.themes["constellations"])
    assert coined.slug == "coined-mountains-constellations"
    assert len(coined.words) == 5


def test_blends_take_gender_from_the_second_word(gen: Generator) -> None:
    tierwelt = gen.themes["tierwelt"]
    blended = gen.blended_theme(tierwelt, tierwelt, 15, "de")
    assert blended.words
    assert len(blended.genders) == len(blended.words)
    names = [
        gen.render(r, blended, 2, 0.0, "de").name
        for r in gen.generate_theme_recipes(blended, 15, "de")
    ]
    assert all(" " in name or len(name) >= 4 for name in names)


def test_blends_cross_two_themes(gen: Generator) -> None:
    berge, stars = gen.themes["mountains"], gen.themes["constellations"]
    blended = gen.blended_theme(berge, stars, 10)
    assert blended.slug == "blend-mountains-constellations"
    assert len(set(w.lower() for w in blended.words)) == len(blended.words)


@pytest.mark.parametrize(
    ("slug", "letters", "language", "words"),
    [
        ("animals", "sm", "en", 2),
        ("animals", "bft", "en", 3),
        ("tierwelt", "gft", "de", 3),
        ("constellations", "o", "en", 1),
    ],
)
def test_acronym_initials(
    gen: Generator, slug: str, letters: str, language: str, words: int
) -> None:
    theme = gen.themes[slug]
    acronym = gen.acronym_theme(theme, letters, language)
    recipes = gen.generate_acronym_recipes(acronym, theme, letters, 12)
    assert recipes
    for recipe in recipes:
        name = gen.render(recipe, acronym, 2, 1.0, language).name
        initials = "".join(part[0].lower() for part in name.split())
        assert initials == letters, name
        assert len(name.split()) == words


def test_acronym_without_matching_words_is_empty(gen: Generator) -> None:
    theme = gen.themes["animals"]
    acronym = gen.acronym_theme(theme, "xq", "en")
    assert acronym.patterns == ()
    assert gen.generate_acronym_recipes(acronym, theme, "xq", 10) == []


def test_acronym_letters_are_capped(gen: Generator) -> None:
    acronym = gen.acronym_theme(gen.themes["animals"], "s.m.t.x", "en")
    assert acronym.name.endswith("SMT")
    assert [Pattern(p) for p in acronym.patterns] == [Pattern.ADJ_THEME_VERB]


def test_german_agents_suffice_for_a_full_stack(gen: Generator) -> None:
    # Deutsch mit Wort vorn kennt nur THEME_AGENT - vorher blieb der Stapel bei 38.
    from codename_generator.generator import AnchorPosition

    recipes = gen.generate_seeded_recipes("Sitemap", 40, "de", AnchorPosition.FRONT)
    assert len(recipes) == 40
