from __future__ import annotations

import random
import re
import zlib
from dataclasses import dataclass
from enum import StrEnum

from codename_generator.phonetic import mutate
from codename_generator.wordlist import WordList, load_modifiers, load_themes

RANDOM_THEME_SLUG = "random"
CUSTOM_SEED_SLUG = "custom-seed"
_MUTATION_RETRIES = 5
_SEED_CEILING = 2**31


class Pattern(StrEnum):
    ADJ_THEME = "adj-theme"
    VERB_THEME = "verb-theme"
    THEME_VERB = "theme-verb"
    THEME_AGENT = "theme-agent"
    THEME_ONLY = "theme"
    ADJ_THEME_VERB = "adj-theme-verb"


# Anzahl der Komponenten (Modifier + Theme-Wort) pro Pattern.
PATTERN_WORD_COUNT: dict[Pattern, int] = {
    Pattern.THEME_ONLY: 1,
    Pattern.ADJ_THEME: 2,
    Pattern.VERB_THEME: 2,
    Pattern.THEME_VERB: 2,
    Pattern.THEME_AGENT: 2,
    Pattern.ADJ_THEME_VERB: 3,
}

# Zwei-Wort-Patterns, aus denen `_select_pattern` zufaellig waehlt.
# Agent-Suffix gehoert dazu - typische Tool-Naming-Konvention (Sitemap Runner).
_TWO_WORD_PATTERNS = (
    Pattern.ADJ_THEME,
    Pattern.VERB_THEME,
    Pattern.THEME_VERB,
    Pattern.THEME_AGENT,
)


@dataclass(frozen=True)
class Recipe:
    """Die stabilen Zutaten eines Vorschlags - unabhaengig von Mutation/Wortzahl.

    Ein Recipe wird einmal zufaellig erzeugt und bleibt erhalten. Erst `render`
    macht daraus eine konkrete Suggestion - mit aktueller Mutation und Wortzahl.
    So aendert ein Slider nur die Darstellung, nicht die Grundzutaten.
    """

    theme_word: str
    adjective: str
    verb: str
    agent: str
    pattern_index: int
    mutation_roll: float
    mutation_seed: int


@dataclass(frozen=True)
class Suggestion:
    name: str
    slug: str
    pattern: Pattern
    mutated: bool
    source_words: tuple[str, ...]


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.lower()).strip("-")


def _compose_name(pattern: Pattern, theme_word: str, modifiers: tuple[str, ...]) -> str:
    """Setzt einen Namen aus Pattern, Theme-Wort und Modifiern zusammen."""
    mods = list(modifiers)
    if pattern == Pattern.THEME_ONLY:
        return theme_word
    if pattern in (Pattern.THEME_VERB, Pattern.THEME_AGENT):
        return f"{theme_word} {mods[0]}" if mods else theme_word
    if pattern == Pattern.ADJ_THEME_VERB:
        if len(mods) >= 2:
            return f"{mods[0]} {theme_word} {mods[1]}"
        return theme_word
    # ADJ_THEME und VERB_THEME: Modifier vorangestellt.
    return f"{mods[0]} {theme_word}" if mods else theme_word


def _patterns_from_strings(values: tuple[str, ...]) -> tuple[Pattern, ...]:
    """Konvertiert Pattern-Strings zu Enums, ungueltige werden uebersprungen."""
    result: list[Pattern] = []
    for value in values:
        try:
            result.append(Pattern(value))
        except ValueError:
            continue
    return tuple(result)


def _build_random_theme(themes: dict[str, WordList]) -> WordList:
    """Virtuelles Random-Theme: alle Woerter aus allen Themes zusammen."""
    pooled = tuple(sorted({w for t in themes.values() for w in t.words}))
    return WordList(
        slug=RANDOM_THEME_SLUG,
        name="Random (all themes)",
        description="Pooled from every theme",
        words=pooled,
    )


@dataclass
class Generator:
    themes: dict[str, WordList]
    modifiers: dict[str, WordList]
    rng: random.Random

    @classmethod
    def load(cls, seed: int | None = None) -> Generator:
        themes = load_themes()
        themes_with_random: dict[str, WordList] = {RANDOM_THEME_SLUG: _build_random_theme(themes)}
        themes_with_random.update(themes)
        return cls(
            themes=themes_with_random,
            modifiers=load_modifiers(),
            rng=random.Random(seed),
        )

    def generate_seeded_recipes(self, seed: str, count: int = 30) -> list[Recipe]:
        """Erzeugt `count` Recipes mit einem festen `seed` als Theme-Wort.

        Anders als `generate_recipes` ist das Theme-Wort vom Benutzer
        vorgegeben (z.B. "Sitemap") - nicht zufaellig aus einer Wortliste.
        Damit alle Vorschlaege trotz gleichen Theme-Worts unterschiedlich
        sind, wird auf der Kombination (adjective, verb, agent, pattern_index)
        dedupliziert. Modifier kommen aus den globalen Pools.
        """
        adjectives = self.modifiers["adjectives"].words
        verbs = self.modifiers["verbs"].words
        agents = self._agent_pool()
        recipes: list[Recipe] = []
        seen: set[tuple[str, str, str, int]] = set()
        attempts = 0
        max_attempts = count * 40
        # Anzahl der Patterns, aus denen gezogen wird - korrespondiert mit
        # _TWO_WORD_PATTERNS in _select_pattern.
        pattern_choices = len(_TWO_WORD_PATTERNS)
        while len(recipes) < count and attempts < max_attempts:
            attempts += 1
            adjective = self.rng.choice(adjectives)
            verb = self.rng.choice(verbs)
            agent = self.rng.choice(agents) if agents else ""
            pattern_index = self.rng.randrange(pattern_choices)
            key = (adjective.lower(), verb.lower(), agent.lower(), pattern_index)
            if key in seen:
                continue
            seen.add(key)
            recipes.append(
                Recipe(
                    theme_word=seed,
                    adjective=adjective,
                    verb=verb,
                    agent=agent,
                    pattern_index=pattern_index,
                    mutation_roll=self.rng.random(),
                    mutation_seed=self.rng.randrange(_SEED_CEILING),
                )
            )
        return recipes

    def _agent_pool(self) -> tuple[str, ...]:
        """Globaler Agent-Pool aus modifiers/agents.yaml (oder leer wenn fehlt)."""
        agents_list = self.modifiers.get("agents")
        return agents_list.words if agents_list else ()

    def seeded_theme(self, seed: str) -> WordList:
        """Erzeugt ein virtuelles WordList fuer das Custom-Seed-Theme.

        Das Theme hat nur das Seed-Wort als Inhalt; Pattern und Mutation
        bleiben offen (gesteuert von den Slidern). Wird vom TUI in
        `Generator.render()` als `theme`-Argument uebergeben.
        """
        return WordList(
            slug=CUSTOM_SEED_SLUG,
            name=f"Custom Seed: {seed}",
            description="your idea combined with adjectives and verbs",
            words=(seed,),
        )

    def generate_recipes(self, theme_slug: str, count: int = 30) -> list[Recipe]:
        """Erzeugt `count` zufaellige Recipes - jedes Theme-Wort nur einmal."""
        if theme_slug not in self.themes:
            raise KeyError(f"Unknown theme: {theme_slug}")
        theme = self.themes[theme_slug]
        adjectives = theme.adjectives or self.modifiers["adjectives"].words
        verbs = theme.verbs or self.modifiers["verbs"].words
        agents = self._agent_pool()
        recipes: list[Recipe] = []
        seen: set[str] = set()
        attempts = 0
        max_attempts = count * 40
        pattern_choices = len(_TWO_WORD_PATTERNS)
        while len(recipes) < count and attempts < max_attempts:
            attempts += 1
            theme_word = self.rng.choice(theme.words)
            key = theme_word.lower()
            if key in seen:
                continue
            seen.add(key)
            recipes.append(
                Recipe(
                    theme_word=theme_word,
                    adjective=self.rng.choice(adjectives),
                    verb=self.rng.choice(verbs),
                    agent=self.rng.choice(agents) if agents else "",
                    pattern_index=self.rng.randrange(pattern_choices),
                    mutation_roll=self.rng.random(),
                    mutation_seed=self.rng.randrange(_SEED_CEILING),
                )
            )
        return recipes

    @staticmethod
    def _select_pattern(theme: WordList, recipe: Recipe, word_count: int) -> Pattern:
        """Waehlt das Pattern so, dass der Name `word_count` SICHTBARE Woerter hat.

        Theme-Woerter koennen selbst mehrteilig sein (z.B. "Hoover Dam" = 2
        Woerter). Damit der Words-Slider die tatsaechliche Wortanzahl steuert,
        wird die Laenge des Theme-Worts beruecksichtigt: die Zahl der Modifier
        ergibt sich aus `word_count` minus der Wortzahl des Theme-Worts.
        """
        # Theme-eigene Patterns haben Vorrang - der Slider ist dann gesperrt.
        if theme.patterns:
            declared = _patterns_from_strings(theme.patterns)
            if declared:
                return declared[recipe.pattern_index % len(declared)]

        theme_word_count = len(recipe.theme_word.split())
        modifiers = word_count - theme_word_count
        if modifiers <= 0:
            # Theme-Wort fuellt das Budget bereits aus (oder ueberschreitet es).
            return Pattern.THEME_ONLY
        if modifiers == 1:
            return _TWO_WORD_PATTERNS[recipe.pattern_index % len(_TWO_WORD_PATTERNS)]
        return Pattern.ADJ_THEME_VERB

    def render(
        self,
        recipe: Recipe,
        theme: WordList,
        word_count: int = 2,
        mutation_chance: float = 0.35,
    ) -> Suggestion:
        """Macht aus einem Recipe eine konkrete Suggestion fuer die aktuellen
        Mutation-/Wortzahl-Einstellungen."""
        pattern = self._select_pattern(theme, recipe, word_count)

        rendered = recipe.theme_word
        mutated = False
        if theme.mutate and recipe.mutation_roll < mutation_chance:
            seeded = random.Random(recipe.mutation_seed)
            for _ in range(_MUTATION_RETRIES):
                candidate = mutate(recipe.theme_word, seeded)
                if candidate != recipe.theme_word:
                    rendered, mutated = candidate, True
                    break

        sources: tuple[str, ...]
        match pattern:
            case Pattern.ADJ_THEME:
                name = f"{recipe.adjective} {rendered}"
                sources = (recipe.theme_word, recipe.adjective)
            case Pattern.VERB_THEME:
                name = f"{recipe.verb} {rendered}"
                sources = (recipe.theme_word, recipe.verb)
            case Pattern.THEME_VERB:
                name = f"{rendered} {recipe.verb}"
                sources = (recipe.theme_word, recipe.verb)
            case Pattern.THEME_AGENT:
                # Agent-Pool kann leer sein (agents.yaml fehlt) - dann auf
                # THEME_VERB ausweichen, statt einen Leerstring anzuhaengen.
                if recipe.agent:
                    name = f"{rendered} {recipe.agent}"
                    sources = (recipe.theme_word, recipe.agent)
                else:
                    name = f"{rendered} {recipe.verb}"
                    sources = (recipe.theme_word, recipe.verb)
            case Pattern.THEME_ONLY:
                name = rendered
                sources = (recipe.theme_word,)
            case Pattern.ADJ_THEME_VERB:
                name = f"{recipe.adjective} {rendered} {recipe.verb}"
                sources = (recipe.theme_word, recipe.adjective, recipe.verb)

        return Suggestion(
            name=name.title(),
            slug=_slugify(name),
            pattern=pattern,
            mutated=mutated,
            source_words=sources,
        )

    def render_favorite(self, favorite: Suggestion, mutation_chance: float) -> Suggestion:
        """Rendert einen Favoriten mit der aktuellen Mutation neu.

        Pattern und Modifier des Favoriten bleiben erhalten - nur das Theme-Wort
        (das erste source_word) wird ggf. phonetisch mutiert. Der Seed wird
        stabil aus dem Slug abgeleitet, sodass derselbe Mutationswert immer das
        gleiche Ergebnis liefert (kein Flackern beim Schieben des Sliders).
        """
        if not favorite.source_words:
            return favorite
        theme_word = favorite.source_words[0]
        modifiers = favorite.source_words[1:]
        rng = random.Random(zlib.crc32(favorite.slug.encode("utf-8")))
        rendered = theme_word
        mutated = False
        if rng.random() < mutation_chance:
            for _ in range(_MUTATION_RETRIES):
                candidate = mutate(theme_word, rng)
                if candidate != theme_word:
                    rendered, mutated = candidate, True
                    break
        name = _compose_name(favorite.pattern, rendered, modifiers)
        return Suggestion(
            name=name.title(),
            slug=_slugify(name),
            pattern=favorite.pattern,
            mutated=mutated,
            source_words=favorite.source_words,
        )

    def suggest(
        self,
        theme_slug: str,
        count: int = 10,
        mutation_chance: float = 0.35,
        word_count: int = 2,
    ) -> list[Suggestion]:
        """Einmalige Generierung: Recipes erzeugen und direkt rendern.

        `word_count` legt die exakte Anzahl der Namens-Komponenten fest (1..3).
        """
        recipes = self.generate_recipes(theme_slug, count)
        theme = self.themes[theme_slug]
        return [self.render(r, theme, word_count, mutation_chance) for r in recipes]
