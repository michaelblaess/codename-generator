from __future__ import annotations

import random
import re
from dataclasses import dataclass
from enum import StrEnum

from codename_generator.phonetic import mutate
from codename_generator.wordlist import WordList, load_modifiers, load_themes


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


@dataclass
class Generator:
    themes: dict[str, WordList]
    modifiers: dict[str, WordList]
    rng: random.Random

    @classmethod
    def load(cls, seed: int | None = None) -> Generator:
        return cls(
            themes=load_themes(),
            modifiers=load_modifiers(),
            rng=random.Random(seed),
        )

    def _pick(self, words: tuple[str, ...]) -> str:
        return self.rng.choice(words)

    def _build(
        self,
        theme: WordList,
        pattern: Pattern,
        mutation_chance: float,
    ) -> Suggestion:
        adjectives = self.modifiers["adjectives"].words
        verbs = self.modifiers["verbs"].words
        theme_word = self._pick(theme.words)
        mutated = self.rng.random() < mutation_chance
        rendered_theme = mutate(theme_word, self.rng) if mutated else theme_word

        sources: tuple[str, ...]
        match pattern:
            case Pattern.ADJ_THEME:
                modifier = self._pick(adjectives)
                name = f"{modifier} {rendered_theme}"
                sources = (modifier, theme_word)
            case Pattern.VERB_THEME:
                modifier = self._pick(verbs)
                name = f"{modifier} {rendered_theme}"
                sources = (modifier, theme_word)
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
        """Generiere `count` Codenamen-Vorschlaege fuer ein Theme."""
        if theme_slug not in self.themes:
            raise KeyError(f"Unknown theme: {theme_slug}")
        theme = self.themes[theme_slug]
        pool = patterns or tuple(Pattern)
        seen: set[str] = set()
        result: list[Suggestion] = []
        attempts = 0
        max_attempts = count * 20
        while len(result) < count and attempts < max_attempts:
            attempts += 1
            pattern = self.rng.choice(pool)
            suggestion = self._build(theme, pattern, mutation_chance)
            if suggestion.slug in seen:
                continue
            seen.add(suggestion.slug)
            result.append(suggestion)
        return result
