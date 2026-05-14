from __future__ import annotations

import random
import re
from dataclasses import dataclass
from enum import StrEnum

from codename_generator.phonetic import mutate
from codename_generator.wordlist import WordList, load_modifiers, load_themes

RANDOM_THEME_SLUG = "random"
_MUTATION_RETRIES = 5


class Pattern(StrEnum):
    ADJ_THEME = "adj-theme"
    VERB_THEME = "verb-theme"
    THEME_VERB = "theme-verb"
    THEME_ONLY = "theme"


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

    def _pick(self, words: tuple[str, ...]) -> str:
        return self.rng.choice(words)

    def _render_theme_word(
        self,
        theme_word: str,
        want_mutation: bool,
    ) -> tuple[str, bool]:
        """Wende Mutation an. Wenn keine Aenderung erreichbar, false zurueck."""
        if not want_mutation:
            return theme_word, False
        for _ in range(_MUTATION_RETRIES):
            candidate = mutate(theme_word, self.rng)
            if candidate != theme_word:
                return candidate, True
        return theme_word, False

    def _build(
        self,
        theme: WordList,
        pattern: Pattern,
        mutation_chance: float,
    ) -> Suggestion:
        adjectives = self.modifiers["adjectives"].words
        verbs = self.modifiers["verbs"].words
        theme_word = self._pick(theme.words)
        # Ohne Modifier waere eine nicht-mutierte Suggestion identisch mit dem
        # Quellwort - dann zwingend mutieren, sonst wird der Vorschlag verworfen.
        force_mutation = pattern is Pattern.THEME_ONLY
        want_mutation = force_mutation or self.rng.random() < mutation_chance
        rendered_theme, mutated = self._render_theme_word(theme_word, want_mutation)

        # source_words[0] ist immer das Theme-Wort, danach folgen Modifier.
        sources: tuple[str, ...]
        match pattern:
            case Pattern.ADJ_THEME:
                modifier = self._pick(adjectives)
                name = f"{modifier} {rendered_theme}"
                sources = (theme_word, modifier)
            case Pattern.VERB_THEME:
                modifier = self._pick(verbs)
                name = f"{modifier} {rendered_theme}"
                sources = (theme_word, modifier)
            case Pattern.THEME_VERB:
                modifier = self._pick(verbs)
                name = f"{rendered_theme} {modifier}"
                sources = (theme_word, modifier)
            case Pattern.THEME_ONLY:
                name = rendered_theme
                sources = (theme_word,)

        return Suggestion(
            name=name.title(),
            slug=_slugify(name),
            pattern=pattern,
            mutated=mutated,
            source_words=sources,
        )

    def suggest(
        self,
        theme_slug: str,
        count: int = 10,
        mutation_chance: float = 0.35,
        patterns: tuple[Pattern, ...] | None = None,
    ) -> list[Suggestion]:
        """Generiere `count` Codenamen-Vorschlaege fuer ein Theme.

        Wenn mutation_chance == 1.0, werden nur Vorschlaege akzeptiert, deren
        Theme-Wort tatsaechlich phonetisch mutiert wurde.
        """
        if theme_slug not in self.themes:
            raise KeyError(f"Unknown theme: {theme_slug}")
        theme = self.themes[theme_slug]
        pool = patterns or tuple(Pattern)
        # Bei 0% Mutation den THEME_ONLY-Pattern weglassen - er wuerde sonst
        # trotzdem ein mutiertes Wort erzeugen (sein Force-Mutation-Pfad).
        if mutation_chance <= 0.0:
            pool = tuple(p for p in pool if p is not Pattern.THEME_ONLY)
            if not pool:
                return []
        seen_slugs: set[str] = set()
        seen_theme_words: set[str] = set()
        result: list[Suggestion] = []
        require_mutation = mutation_chance >= 1.0
        attempts = 0
        max_attempts = count * 40
        while len(result) < count and attempts < max_attempts:
            attempts += 1
            pattern = self.rng.choice(pool)
            suggestion = self._build(theme, pattern, mutation_chance)
            if suggestion.slug in seen_slugs:
                continue
            if require_mutation and not suggestion.mutated:
                continue
            # Bare source word ohne Modifier und ohne Mutation -> kein Vorschlag.
            if pattern is Pattern.THEME_ONLY and not suggestion.mutated:
                continue
            # Jedes Quellwort des Themes darf nur einmal vorkommen -
            # sonst tauchen mehrere Mutationen desselben Wortes auf
            # (z.B. "Forrego" und "Foreggo" aus "Forego").
            theme_word = suggestion.source_words[0].lower()
            if theme_word in seen_theme_words:
                continue
            seen_slugs.add(suggestion.slug)
            seen_theme_words.add(theme_word)
            result.append(suggestion)
        return result
