from __future__ import annotations

import random
import re
import unicodedata
import zlib
from dataclasses import dataclass
from enum import StrEnum

from codename_generator.grammar import GERMAN, inflect_attribute
from codename_generator.phonetic import mutate
from codename_generator.wordlist import (
    DEFAULT_LANGUAGE,
    WordList,
    load_all_modifiers,
    load_themes,
)

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
    # Beide Modifier vorangestellt - die deutsche Entsprechung zu
    # ADJ_THEME_VERB ("Stiller Jagender Falke" statt "Silent Falcon Runs").
    ADJ_VERB_THEME = "adj-verb-theme"


# Anzahl der Komponenten (Modifier + Theme-Wort) pro Pattern.
PATTERN_WORD_COUNT: dict[Pattern, int] = {
    Pattern.THEME_ONLY: 1,
    Pattern.ADJ_THEME: 2,
    Pattern.VERB_THEME: 2,
    Pattern.THEME_VERB: 2,
    Pattern.THEME_AGENT: 2,
    Pattern.ADJ_THEME_VERB: 3,
    Pattern.ADJ_VERB_THEME: 3,
}

# Zwei-Wort-Patterns, aus denen `_select_pattern` zufaellig waehlt.
# Agent-Suffix gehoert dazu - typische Tool-Naming-Konvention (Sitemap Runner).
_TWO_WORD_PATTERNS = (
    Pattern.ADJ_THEME,
    Pattern.VERB_THEME,
    Pattern.THEME_VERB,
    Pattern.THEME_AGENT,
)

# Deutsch kennt kein nachgestelltes Partizip: "Falke Jagend" ist keine
# Wortstellung, "Jagender Falke" schon. THEME_VERB faellt daher weg.
_TWO_WORD_PATTERNS_DE = (
    Pattern.ADJ_THEME,
    Pattern.VERB_THEME,
    Pattern.THEME_AGENT,
)

_TWO_WORD_PATTERNS_BY_LANGUAGE: dict[str, tuple[Pattern, ...]] = {
    GERMAN: _TWO_WORD_PATTERNS_DE,
}

_THREE_WORD_PATTERN_BY_LANGUAGE: dict[str, Pattern] = {
    GERMAN: Pattern.ADJ_VERB_THEME,
}


def _two_word_patterns(language: str) -> tuple[Pattern, ...]:
    """Zwei-Wort-Patterns der Sprache (Fallback: die englische Auswahl)."""
    return _TWO_WORD_PATTERNS_BY_LANGUAGE.get(language, _TWO_WORD_PATTERNS)


def _three_word_pattern(language: str) -> Pattern:
    """Drei-Wort-Pattern der Sprache (Fallback: die englische Wortstellung)."""
    return _THREE_WORD_PATTERN_BY_LANGUAGE.get(language, Pattern.ADJ_THEME_VERB)


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

# Zeichen, die im Slug ausgeschrieben gehoeren statt zerlegt zu werden:
# "ue" ist ein brauchbarer Slug fuer "ue-Umlaut", ein blankes "u" nicht.
_TRANSLITERATIONS = str.maketrans(
    {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "æ": "ae",
        "œ": "oe",
        "ø": "oe",
    }
)


def _slugify(text: str) -> str:
    """Erzeugt einen ASCII-Slug - Umlaute werden ausgeschrieben, nicht entfernt.

    Ohne Transliteration wuerde die Slug-Regex aus "Gruener Blitz" (mit
    Umlaut) ein "gr-ner-blitz" machen, weil sie nur [a-z0-9] kennt.
    """
    lowered = text.lower().translate(_TRANSLITERATIONS)
    # Was die Tabelle nicht kennt (Akzente aller Art), wird zerlegt und die
    # kombinierenden Zeichen fallen weg: "e" bleibt uebrig.
    decomposed = unicodedata.normalize("NFKD", lowered)
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _SLUG_RE.sub("-", ascii_only).strip("-")


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
    if pattern == Pattern.ADJ_VERB_THEME:
        if len(mods) >= 2:
            return f"{mods[0]} {mods[1]} {theme_word}"
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


def _random_slug(language: str) -> str:
    """Slug des Random-Themes einer Sprache (`random`, `random-de`, ...)."""
    return RANDOM_THEME_SLUG if language == DEFAULT_LANGUAGE else f"{RANDOM_THEME_SLUG}-{language}"


def _build_random_theme(themes: dict[str, WordList], language: str) -> WordList:
    """Virtuelles Random-Theme: alle Woerter EINER Sprache zusammen.

    Sprachen bleiben getrennt, sonst wuerde ein deutsches Wort mit englischen
    Modifiern kombiniert (und umgekehrt).
    """
    # Genus mitnehmen, sonst verliert der Pool die Flexionsinformation.
    pooled: dict[str, str] = {}
    for theme in themes.values():
        if theme.language != language:
            continue
        for word in theme.words:
            pooled.setdefault(word, theme.gender_of(word))
    words = tuple(sorted(pooled))
    return WordList(
        slug=_random_slug(language),
        name=f"Random ({language.upper()} themes)",
        description=f"Pooled from every {language.upper()} theme",
        words=words,
        language=language,
        genders=tuple(pooled[w] for w in words) if any(pooled.values()) else (),
        # Die phonetische Mutation ist auf englisch-lateinische Endungen
        # zugeschnitten - andere Sprachen starten daher bei 0 (per Slider
        # weiterhin zuschaltbar).
        default_mutation=None if language == DEFAULT_LANGUAGE else 0,
    )


@dataclass
class Generator:
    themes: dict[str, WordList]
    # Modifier-Pools nach Sprache: modifiers["de"]["adjectives"].
    modifiers: dict[str, dict[str, WordList]]
    rng: random.Random

    @classmethod
    def load(cls, seed: int | None = None) -> Generator:
        themes = load_themes()
        # Pro Sprache ein Random-Theme, damit nichts sprachuebergreifend mischt.
        # Die Default-Sprache steht vorn - ihr Random-Theme ist der Startpunkt
        # der Theme-Liste.
        languages = sorted(
            {t.language for t in themes.values()},
            key=lambda lang: (lang != DEFAULT_LANGUAGE, lang),
        )
        themes_with_random: dict[str, WordList] = {
            _random_slug(language): _build_random_theme(themes, language) for language in languages
        }
        themes_with_random.update(themes)
        return cls(
            themes=themes_with_random,
            modifiers=load_all_modifiers(),
            rng=random.Random(seed),
        )

    def _modifier_pool(self, language: str, role: str) -> tuple[str, ...]:
        """Woerter eines Modifier-Pools, mit Rueckfall auf die Default-Sprache."""
        pools = self.modifiers.get(language) or self.modifiers.get(DEFAULT_LANGUAGE, {})
        wordlist = pools.get(role)
        return wordlist.words if wordlist else ()

    def generate_seeded_recipes(
        self, seed: str, count: int = 30, language: str = DEFAULT_LANGUAGE
    ) -> list[Recipe]:
        """Erzeugt `count` Recipes mit einem festen `seed` als Theme-Wort.

        Anders als `generate_recipes` ist das Theme-Wort vom Benutzer
        vorgegeben (z.B. "Sitemap") - nicht zufaellig aus einer Wortliste.
        Damit alle Vorschlaege trotz gleichen Theme-Worts unterschiedlich
        sind, wird auf der Kombination (adjective, verb, agent, pattern_index)
        dedupliziert. Modifier kommen aus den Pools der uebergebenen Sprache.
        """
        adjectives = self._modifier_pool(language, "adjectives")
        verbs = self._modifier_pool(language, "verbs")
        agents = self._modifier_pool(language, "agents")
        recipes: list[Recipe] = []
        seen: set[tuple[str, str, str, int]] = set()
        attempts = 0
        max_attempts = count * 40
        # Anzahl der Patterns, aus denen gezogen wird - korrespondiert mit
        # _two_word_patterns in _select_pattern.
        pattern_choices = len(_two_word_patterns(language))
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

    def seeded_theme(self, seed: str, language: str = DEFAULT_LANGUAGE) -> WordList:
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
            language=language,
        )

    def generate_recipes(self, theme_slug: str, count: int = 30) -> list[Recipe]:
        """Erzeugt `count` zufaellige Recipes - jedes Theme-Wort nur einmal."""
        if theme_slug not in self.themes:
            raise KeyError(f"Unknown theme: {theme_slug}")
        theme = self.themes[theme_slug]
        adjectives = theme.adjectives or self._modifier_pool(theme.language, "adjectives")
        verbs = theme.verbs or self._modifier_pool(theme.language, "verbs")
        agents = self._modifier_pool(theme.language, "agents")
        recipes: list[Recipe] = []
        seen: set[str] = set()
        attempts = 0
        max_attempts = count * 40
        pattern_choices = len(_two_word_patterns(theme.language))
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
            choices = _two_word_patterns(theme.language)
            return choices[recipe.pattern_index % len(choices)]
        return _three_word_pattern(theme.language)

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

        # Vorangestellte Modifier werden gebeugt (nur Sprachen mit Flexion,
        # siehe grammar.py). Das Genus haengt am Original-Wort, nicht an der
        # mutierten Form. Die gebeugte Form wandert auch in `sources`, damit
        # ein Favorit spaeter ohne Theme-Kontext korrekt gerendert wird.
        gender = theme.gender_of(recipe.theme_word)
        adjective = inflect_attribute(recipe.adjective, gender, theme.language)
        attributive_verb = inflect_attribute(recipe.verb, gender, theme.language)

        sources: tuple[str, ...]
        match pattern:
            case Pattern.ADJ_THEME:
                name = f"{adjective} {rendered}"
                sources = (recipe.theme_word, adjective)
            case Pattern.VERB_THEME:
                name = f"{attributive_verb} {rendered}"
                sources = (recipe.theme_word, attributive_verb)
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
                name = f"{adjective} {rendered} {recipe.verb}"
                sources = (recipe.theme_word, adjective, recipe.verb)
            case Pattern.ADJ_VERB_THEME:
                name = f"{adjective} {attributive_verb} {rendered}"
                sources = (recipe.theme_word, adjective, attributive_verb)

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
