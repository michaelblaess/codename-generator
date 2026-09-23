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
    NEUTRAL_LANGUAGE,
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
    # Anker: ein eigenes Wort zusammen mit einem Wort aus einem Thema
    # ("Sitemap Orion", "Orion Sitemap"). Der Anker wird nie gebeugt - aus
    # "Sitemap" darf im Deutschen kein "Sitemaper" werden.
    ANCHOR_THEME = "anchor-theme"
    THEME_ANCHOR = "theme-anchor"


class VariantKeep(StrEnum):
    """Was beim Variieren eines Treffers stehen bleibt."""

    # Das Theme-Wort bleibt, Zusaetze und Pattern werden neu gewuerfelt.
    WORD = "word"
    # Zusaetze und Pattern bleiben, das Theme-Wort wechselt.
    MODIFIER = "modifier"


class AnchorPosition(StrEnum):
    """Wo das eigene Wort im Namen steht."""

    ANY = "any"
    FRONT = "front"
    BACK = "back"


# Anzahl der Komponenten (Modifier + Theme-Wort) pro Pattern.
PATTERN_WORD_COUNT: dict[Pattern, int] = {
    Pattern.THEME_ONLY: 1,
    Pattern.ADJ_THEME: 2,
    Pattern.VERB_THEME: 2,
    Pattern.THEME_VERB: 2,
    Pattern.THEME_AGENT: 2,
    Pattern.ADJ_THEME_VERB: 3,
    Pattern.ADJ_VERB_THEME: 3,
    Pattern.ANCHOR_THEME: 2,
    Pattern.THEME_ANCHOR: 2,
}

# Zwei-Wort-Patterns, deren Modifier VOR dem Theme-Wort steht. Beim eigenen
# Wort heisst das: das Wort steht hinten ("Silent Sitemap").
_PREFIX_PATTERNS = frozenset({Pattern.ADJ_THEME, Pattern.VERB_THEME})

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


def anchor_modifier_patterns(language: str, position: AnchorPosition) -> tuple[Pattern, ...]:
    """Zwei-Wort-Patterns fuer ein eigenes Wort mit Zusaetzen, gefiltert nach Position.

    FRONT stellt das Wort nach vorn ("Sitemap Runner"), BACK nach hinten
    ("Silent Sitemap"), ANY laesst alle Patterns der Sprache zu.
    """
    patterns = _two_word_patterns(language)
    if position == AnchorPosition.FRONT:
        return tuple(p for p in patterns if p not in _PREFIX_PATTERNS)
    if position == AnchorPosition.BACK:
        return tuple(p for p in patterns if p in _PREFIX_PATTERNS)
    return patterns


def anchor_theme_patterns(position: AnchorPosition) -> tuple[Pattern, ...]:
    """Patterns fuer ein eigenes Wort mit einem Partner-Thema, gefiltert nach Position."""
    if position == AnchorPosition.FRONT:
        return (Pattern.ANCHOR_THEME,)
    if position == AnchorPosition.BACK:
        return (Pattern.THEME_ANCHOR,)
    return (Pattern.ANCHOR_THEME, Pattern.THEME_ANCHOR)


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
    # Eigenes Wort bei ANCHOR_THEME / THEME_ANCHOR, sonst leer.
    anchor: str = ""


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


def _visible_modifier(pattern: Pattern, adjective: str, verb: str, agent: str) -> tuple[str, str]:
    """Position und Modifier, die ein Zwei-Wort-Pattern tatsaechlich im Namen zeigt.

    Die Position gehoert mit in den Schluessel, das Pattern nicht: manche Woerter
    stehen in zwei Pools ("forge" ist Verb und Agent, "flackernd" Adjektiv und
    Verb) und ergaeben sonst ueber zwei Patterns denselben Namen.
    """
    if pattern == Pattern.ADJ_THEME:
        return ("prefix", adjective.lower())
    if pattern == Pattern.VERB_THEME:
        return ("prefix", verb.lower())
    # THEME_VERB und THEME_AGENT haengen an, ohne Agent-Pool das Verb.
    return ("suffix", agent.lower() if pattern == Pattern.THEME_AGENT and agent else verb.lower())


def _compose_name(pattern: Pattern, theme_word: str, modifiers: tuple[str, ...]) -> str:
    """Setzt einen Namen aus Pattern, Theme-Wort und Modifiern zusammen."""
    mods = list(modifiers)
    if pattern == Pattern.THEME_ONLY:
        return theme_word
    if pattern in (Pattern.THEME_VERB, Pattern.THEME_AGENT, Pattern.THEME_ANCHOR):
        return f"{theme_word} {mods[0]}" if mods else theme_word
    if pattern == Pattern.ADJ_THEME_VERB:
        if len(mods) >= 2:
            return f"{mods[0]} {theme_word} {mods[1]}"
        return theme_word
    if pattern == Pattern.ADJ_VERB_THEME:
        if len(mods) >= 2:
            return f"{mods[0]} {mods[1]} {theme_word}"
        return theme_word
    # ADJ_THEME, VERB_THEME und ANCHOR_THEME: Modifier vorangestellt.
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


def effective_language(theme: WordList, language: str | None = None) -> str:
    """Sprache, in der ein Theme benannt wird.

    Ein sprachgebundenes Theme bestimmt sie selbst - ein deutsches Theme bleibt
    deutsch, egal was eingestellt ist. Nur neutrale Themes (Eigennamen) folgen
    der gewaehlten Sprache.
    """
    if theme.language != NEUTRAL_LANGUAGE:
        return theme.language
    return language or DEFAULT_LANGUAGE


def _random_slug(language: str) -> str:
    """Slug des Random-Themes einer Sprache (`random`, `random-de`, ...)."""
    return RANDOM_THEME_SLUG if language == DEFAULT_LANGUAGE else f"{RANDOM_THEME_SLUG}-{language}"


def _build_random_theme(themes: dict[str, WordList], language: str) -> WordList:
    """Virtuelles Random-Theme: die Woerter EINER Sprache plus die neutralen.

    Sprachgebundene Themes bleiben getrennt, sonst wuerde ein deutsches Wort
    mit englischen Modifiern kombiniert (und umgekehrt). Neutrale Themes
    (Eigennamen) gehoeren in jeden Pool.
    """
    # Genus mitnehmen, sonst verliert der Pool die Flexionsinformation.
    pooled: dict[str, str] = {}
    for theme in themes.values():
        if theme.language not in (language, NEUTRAL_LANGUAGE):
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
        modifiers = load_all_modifiers()
        # Pro Sprache ein Random-Theme, damit nichts sprachuebergreifend mischt.
        # Die Default-Sprache steht vorn - ihr Random-Theme ist der Startpunkt
        # der Theme-Liste.
        languages = sorted(modifiers, key=lambda lang: (lang != DEFAULT_LANGUAGE, lang))
        themes_with_random: dict[str, WordList] = {
            _random_slug(language): _build_random_theme(themes, language) for language in languages
        }
        themes_with_random.update(themes)
        return cls(
            themes=themes_with_random,
            modifiers=modifiers,
            rng=random.Random(seed),
        )

    def languages(self) -> tuple[str, ...]:
        """Sprachen, in denen generiert werden kann - Default-Sprache zuerst."""
        return tuple(sorted(self.modifiers, key=lambda lang: (lang != DEFAULT_LANGUAGE, lang)))

    def _modifier_pool(self, language: str, role: str) -> tuple[str, ...]:
        """Woerter eines Modifier-Pools, mit Rueckfall auf die Default-Sprache."""
        pools = self.modifiers.get(language) or self.modifiers.get(DEFAULT_LANGUAGE, {})
        wordlist = pools.get(role)
        return wordlist.words if wordlist else ()

    def generate_seeded_recipes(
        self,
        seed: str,
        count: int = 30,
        language: str = DEFAULT_LANGUAGE,
        position: AnchorPosition = AnchorPosition.ANY,
    ) -> list[Recipe]:
        """Erzeugt `count` Recipes mit einem festen `seed` als Theme-Wort.

        Anders als `generate_recipes` ist das Theme-Wort vom Benutzer
        vorgegeben (z.B. "Sitemap") - nicht zufaellig aus einer Wortliste.
        Damit alle Vorschlaege trotz gleichen Theme-Worts unterschiedlich
        sind, wird auf dem dedupliziert, was im Namen tatsaechlich sichtbar
        ist - bei zwei Woertern der eine Modifier des Patterns, bei drei
        Woertern Adjektiv plus Verb. Die ganze Kombination als Schluessel
        reichte nicht: zwei Recipes mit gleichem Adjektiv und verschiedenem
        Verb ergaben zweimal "Silent Sitemap". Modifier kommen aus den Pools
        der uebergebenen Sprache. `position` muss dieselbe sein wie beim
        passenden `seeded_theme`, sonst zeigen Index und Pattern auseinander.
        """
        return self._modifier_recipes(
            seed,
            count,
            anchor_modifier_patterns(language, position),
            self._modifier_pool(language, "adjectives"),
            self._modifier_pool(language, "verbs"),
            self._modifier_pool(language, "agents"),
        )

    def _modifier_recipes(
        self,
        theme_word: str,
        count: int,
        two_word_patterns: tuple[Pattern, ...],
        adjectives: tuple[str, ...],
        verbs: tuple[str, ...],
        agents: tuple[str, ...],
        exclude: Recipe | None = None,
    ) -> list[Recipe]:
        """Recipes mit festem Theme-Wort und wechselnden Zusaetzen, ohne sichtbare Dublette.

        `two_word_patterns` ist die Liste, in die `pattern_index` zeigt - dieselbe,
        die `_select_pattern` spaeter benutzt. `exclude` ist ein Recipe, dessen
        sichtbarer Name nicht noch einmal vorkommen soll (der Treffer, von dem
        aus variiert wird). Die Zugfolge des Zufalls ist die alte aus
        `generate_seeded_recipes` - daran haengen die Permalinks im Web.
        """
        recipes: list[Recipe] = []
        seen_two: set[tuple[str, str]] = set()
        seen_three: set[tuple[str, str]] = set()
        pattern_choices = len(two_word_patterns)
        if exclude is not None:
            excluded = two_word_patterns[exclude.pattern_index % pattern_choices]
            seen_two.add(
                _visible_modifier(excluded, exclude.adjective, exclude.verb, exclude.agent)
            )
            seen_three.add((exclude.adjective.lower(), exclude.verb.lower()))
        attempts = 0
        max_attempts = count * 40
        while len(recipes) < count and attempts < max_attempts:
            attempts += 1
            adjective = self.rng.choice(adjectives)
            verb = self.rng.choice(verbs)
            agent = self.rng.choice(agents) if agents else ""
            pattern_index = self.rng.randrange(pattern_choices)
            pattern = two_word_patterns[pattern_index]
            key_two = _visible_modifier(pattern, adjective, verb, agent)
            key_three = (adjective.lower(), verb.lower())
            if key_two in seen_two or key_three in seen_three:
                continue
            seen_two.add(key_two)
            seen_three.add(key_three)
            recipes.append(
                Recipe(
                    theme_word=theme_word,
                    adjective=adjective,
                    verb=verb,
                    agent=agent,
                    pattern_index=pattern_index,
                    mutation_roll=self.rng.random(),
                    mutation_seed=self.rng.randrange(_SEED_CEILING),
                )
            )
        return recipes

    def seeded_theme(
        self,
        seed: str,
        language: str = DEFAULT_LANGUAGE,
        position: AnchorPosition = AnchorPosition.ANY,
    ) -> WordList:
        """Erzeugt ein virtuelles WordList fuer das Custom-Seed-Theme.

        Das Theme hat nur das Seed-Wort als Inhalt. Bei ANY bleiben Pattern und
        Mutation offen (gesteuert von den Slidern). Eine feste Position legt die
        Patterns fest und damit zwei Woerter - wie bei einem Theme, das eigene
        Patterns mitbringt. Wird vom TUI in `Generator.render()` als
        `theme`-Argument uebergeben.
        """
        patterns = (
            ()
            if position == AnchorPosition.ANY
            else tuple(p.value for p in anchor_modifier_patterns(language, position))
        )
        return WordList(
            slug=CUSTOM_SEED_SLUG,
            name=f"Custom Seed: {seed}",
            description="your idea combined with adjectives and verbs",
            words=(seed,),
            patterns=patterns,
            language=language,
        )

    def anchored_theme(
        self,
        anchor: str,
        partner: WordList,
        language: str | None = None,
        position: AnchorPosition = AnchorPosition.ANY,
    ) -> WordList:
        """Virtuelles Theme: das eigene Wort zusammen mit den Woertern eines Partner-Themas.

        Die Woerter, Genera und Mutationsregeln kommen vom Partner, die
        Patterns legen die Stellung des eigenen Worts fest ("Sitemap Orion"
        oder "Orion Sitemap"). Mutiert wird nur das Wort des Partners.
        """
        return WordList(
            slug=f"{CUSTOM_SEED_SLUG}-{partner.slug}",
            name=f"{anchor} + {partner.name}",
            description=partner.description,
            words=partner.words,
            patterns=tuple(p.value for p in anchor_theme_patterns(position)),
            mutate=partner.mutate,
            default_mutation=partner.default_mutation,
            language=effective_language(partner, language),
            genders=partner.genders,
        )

    def generate_anchored_recipes(
        self,
        anchor: str,
        partner: WordList,
        count: int = 30,
        position: AnchorPosition = AnchorPosition.ANY,
    ) -> list[Recipe]:
        """Recipes aus eigenem Wort und Partner-Thema, jedes Partner-Wort hoechstens einmal.

        Ein Partner-Wort, das dem eigenen Wort gleicht, faellt weg - sonst kaeme
        "Orion Orion" heraus.
        """
        pattern_choices = len(anchor_theme_patterns(position))
        candidates = [w for w in partner.words if w.casefold() != anchor.casefold()]
        recipes: list[Recipe] = []
        seen: set[str] = set()
        attempts = 0
        max_attempts = count * 40
        while candidates and len(recipes) < count and attempts < max_attempts:
            attempts += 1
            word = self.rng.choice(candidates)
            if word.casefold() in seen:
                continue
            seen.add(word.casefold())
            recipes.append(
                Recipe(
                    theme_word=word,
                    adjective="",
                    verb="",
                    agent="",
                    pattern_index=self.rng.randrange(pattern_choices),
                    mutation_roll=self.rng.random(),
                    mutation_seed=self.rng.randrange(_SEED_CEILING),
                    anchor=anchor,
                )
            )
        return recipes

    def crossed_theme(
        self, first: WordList, second: WordList, language: str | None = None
    ) -> WordList:
        """Virtuelles Theme: zwei Themes gekreuzt ("Taurus Orion", "Orion Taurus").

        Technisch ein Anker, der wechselt: das Wort aus `first` steht als Anker
        im Recipe, das aus `second` als Theme-Wort. Damit gelten Genus,
        Mutation und Sprache von `second`, und mutiert wird nur dessen Wort.
        """
        return WordList(
            slug=f"mix-{first.slug}-{second.slug}",
            name=f"{first.name} x {second.name}",
            description=f"{first.name} crossed with {second.name}",
            words=second.words,
            patterns=tuple(p.value for p in anchor_theme_patterns(AnchorPosition.ANY)),
            mutate=second.mutate,
            default_mutation=second.default_mutation,
            language=effective_language(second, language),
            genders=second.genders,
        )

    def generate_crossed_recipes(
        self, first: WordList, second: WordList, count: int = 30
    ) -> list[Recipe]:
        """Recipes aus je einem Wort beider Themes - jedes Wort hoechstens einmal.

        Beide Seiten ohne Wiederholung, sonst stuende ein kurzes Theme in jedem
        zweiten Namen. Ein Wort, das in beiden Themes vorkommt, wird nie mit
        sich selbst gekreuzt.
        """
        pattern_choices = len(anchor_theme_patterns(AnchorPosition.ANY))
        recipes: list[Recipe] = []
        seen_first: set[str] = set()
        seen_second: set[str] = set()
        attempts = 0
        max_attempts = count * 40
        while first.words and second.words and len(recipes) < count and attempts < max_attempts:
            attempts += 1
            anchor = self.rng.choice(first.words)
            word = self.rng.choice(second.words)
            if (
                anchor.casefold() == word.casefold()
                or anchor.casefold() in seen_first
                or word.casefold() in seen_second
            ):
                continue
            seen_first.add(anchor.casefold())
            seen_second.add(word.casefold())
            recipes.append(
                Recipe(
                    theme_word=word,
                    adjective="",
                    verb="",
                    agent="",
                    pattern_index=self.rng.randrange(pattern_choices),
                    mutation_roll=self.rng.random(),
                    mutation_seed=self.rng.randrange(_SEED_CEILING),
                    anchor=anchor,
                )
            )
        return recipes

    def generate_recipes(
        self, theme_slug: str, count: int = 30, language: str | None = None
    ) -> list[Recipe]:
        """Erzeugt `count` zufaellige Recipes - jedes Theme-Wort nur einmal.

        `language` greift nur bei neutralen Themes (Eigennamen) - sie ziehen
        die Modifier der gewaehlten Sprache.
        """
        if theme_slug not in self.themes:
            raise KeyError(f"Unknown theme: {theme_slug}")
        theme = self.themes[theme_slug]
        lang = effective_language(theme, language)
        adjectives = theme.adjectives or self._modifier_pool(lang, "adjectives")
        verbs = theme.verbs or self._modifier_pool(lang, "verbs")
        agents = self._modifier_pool(lang, "agents")
        recipes: list[Recipe] = []
        seen: set[str] = set()
        attempts = 0
        max_attempts = count * 40
        pattern_choices = len(_two_word_patterns(lang))
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

    def generate_variant_recipes(
        self,
        base: Recipe,
        theme: WordList,
        keep: VariantKeep,
        count: int = 30,
        language: str | None = None,
    ) -> list[Recipe]:
        """Varianten eines Treffers: ein Teil bleibt stehen, der andere wird neu gewuerfelt.

        WORD haelt das Theme-Wort und zieht neue Zusaetze aus denselben Pools
        wie `generate_recipes` - das Genus kommt weiter aus dem Theme, die
        Beugung stimmt also. MODIFIER haelt Adjektiv, Verb, Agent, Anker und
        Pattern und zieht neue Theme-Woerter. Der Ausgangstreffer selbst kommt
        in beiden Faellen nicht noch einmal vor.
        """
        if keep == VariantKeep.MODIFIER:
            return self._variant_theme_words(base, theme, count)
        # Bei einem Anker-Treffer ("Sitemap Selene") wuerden neue Zusaetze den
        # Anker verdraengen - dort gibt es nur "Zusatz halten".
        if base.anchor:
            return []
        lang = effective_language(theme, language)
        declared = _patterns_from_strings(theme.patterns)
        # Ein Theme, das nur einzelne Woerter kennt (Power words), hat nichts
        # zum Variieren - jeder Name waere wieder dasselbe Wort.
        if declared and all(PATTERN_WORD_COUNT[p] <= 1 for p in declared):
            return []
        return self._modifier_recipes(
            base.theme_word,
            count,
            declared or _two_word_patterns(lang),
            theme.adjectives or self._modifier_pool(lang, "adjectives"),
            theme.verbs or self._modifier_pool(lang, "verbs"),
            self._modifier_pool(lang, "agents"),
            exclude=base,
        )

    def _variant_theme_words(self, base: Recipe, theme: WordList, count: int) -> list[Recipe]:
        """Recipes mit den Zusaetzen von `base` und anderen Woertern aus `theme`."""
        candidates = [w for w in theme.words if w.casefold() != base.theme_word.casefold()]
        if base.anchor:
            candidates = [w for w in candidates if w.casefold() != base.anchor.casefold()]
        recipes: list[Recipe] = []
        seen: set[str] = set()
        attempts = 0
        max_attempts = count * 40
        while candidates and len(recipes) < count and attempts < max_attempts:
            attempts += 1
            word = self.rng.choice(candidates)
            if word.casefold() in seen:
                continue
            seen.add(word.casefold())
            recipes.append(
                Recipe(
                    theme_word=word,
                    adjective=base.adjective,
                    verb=base.verb,
                    agent=base.agent,
                    pattern_index=base.pattern_index,
                    mutation_roll=self.rng.random(),
                    mutation_seed=self.rng.randrange(_SEED_CEILING),
                    anchor=base.anchor,
                )
            )
        return recipes

    @staticmethod
    def _select_pattern(
        theme: WordList, recipe: Recipe, word_count: int, language: str | None = None
    ) -> Pattern:
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
        lang = effective_language(theme, language)
        if modifiers == 1:
            choices = _two_word_patterns(lang)
            return choices[recipe.pattern_index % len(choices)]
        return _three_word_pattern(lang)

    def render(
        self,
        recipe: Recipe,
        theme: WordList,
        word_count: int = 2,
        mutation_chance: float = 0.35,
        language: str | None = None,
    ) -> Suggestion:
        """Macht aus einem Recipe eine konkrete Suggestion fuer die aktuellen
        Mutation-/Wortzahl-Einstellungen.

        `language` wirkt nur auf neutrale Themes (Eigennamen) - sie werden in
        der gewaehlten Sprache gebeugt und angeordnet.
        """
        pattern = self._select_pattern(theme, recipe, word_count, language)

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
        lang = effective_language(theme, language)
        gender = theme.gender_of(recipe.theme_word)
        adjective = inflect_attribute(recipe.adjective, gender, lang)
        attributive_verb = inflect_attribute(recipe.verb, gender, lang)

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
            # Der Anker bleibt ungebeugt, er ist ein Name und kein Attribut.
            case Pattern.ANCHOR_THEME:
                name = f"{recipe.anchor} {rendered}"
                sources = (recipe.theme_word, recipe.anchor)
            case Pattern.THEME_ANCHOR:
                name = f"{rendered} {recipe.anchor}"
                sources = (recipe.theme_word, recipe.anchor)

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
        language: str | None = None,
    ) -> list[Suggestion]:
        """Einmalige Generierung: Recipes erzeugen und direkt rendern.

        `word_count` legt die exakte Anzahl der Namens-Komponenten fest (1..3).
        `language` wirkt nur auf neutrale Themes (Eigennamen).
        """
        recipes = self.generate_recipes(theme_slug, count, language)
        theme = self.themes[theme_slug]
        return [self.render(r, theme, word_count, mutation_chance, language) for r in recipes]
