from __future__ import annotations

import random
import re

VOWELS = "aeiouy"

_VOWEL_SWAPS: dict[str, tuple[str, ...]] = {
    "a": ("o", "e"),
    "e": ("i", "a"),
    "i": ("e", "y"),
    "o": ("a", "u"),
    "u": ("o", "a"),
    "y": ("i",),
}

_SUFFIX_SWAPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("us", ("os", "as", "yr")),
    ("os", ("us", "as")),
    ("as", ("us", "os")),
    ("a", ("ya", "ah")),
    ("on", ("an", "yn")),
    ("ar", ("or", "ur")),
    ("er", ("ar", "ir")),
    ("is", ("ys", "es")),
)

_DOUBLE_CONSONANT_RE = re.compile(r"[bcdfgklmnprstvz]")


def _swap_random_vowel(word: str, rng: random.Random) -> str:
    indices = [i for i, ch in enumerate(word) if ch.lower() in _VOWEL_SWAPS]
    if not indices:
        return word
    idx = rng.choice(indices)
    original = word[idx].lower()
    replacement = rng.choice(_VOWEL_SWAPS[original])
    if word[idx].isupper():
        replacement = replacement.upper()
    return word[:idx] + replacement + word[idx + 1 :]


def _swap_suffix(word: str, rng: random.Random) -> str:
    lower = word.lower()
    candidates = [(suffix, alts) for suffix, alts in _SUFFIX_SWAPS if lower.endswith(suffix)]
    if not candidates:
        return word
    suffix, alts = rng.choice(candidates)
    replacement = rng.choice(alts)
    if word[-1].isupper():
        replacement = replacement.upper()
    return word[: -len(suffix)] + replacement


def _double_consonant(word: str, rng: random.Random) -> str:
    indices = [
        i
        for i in range(1, len(word) - 1)
        if _DOUBLE_CONSONANT_RE.fullmatch(word[i].lower())
        and word[i - 1].lower() in VOWELS
        and word[i + 1].lower() in VOWELS
    ]
    if not indices:
        return word
    idx = rng.choice(indices)
    return word[: idx + 1] + word[idx] + word[idx + 1 :]


def _drop_last_syllable(word: str, rng: random.Random) -> str:
    """Schneide die letzte Silbe ab und behalte einen Vokal am Wortende."""
    if len(word) < 7:
        return word
    vowel_positions = [i for i, ch in enumerate(word) if ch.lower() in VOWELS]
    if len(vowel_positions) < 2:
        return word
    cut = vowel_positions[-2] + 1
    if cut < 4:
        return word
    return word[:cut]


_MUTATIONS = (_swap_random_vowel, _swap_suffix, _double_consonant, _drop_last_syllable)


def mutate(word: str, rng: random.Random | None = None, intensity: int = 1) -> str:
    """Wende 1..N zufaellige phonetische Mutationen auf das Wort an.

    intensity = Anzahl der hintereinander angewandten Mutationen.
    """
    rng = rng or random.Random()
    if intensity < 1:
        return word
    current = word
    chosen = rng.sample(_MUTATIONS, k=min(intensity, len(_MUTATIONS)))
    for mutation in chosen:
        candidate = mutation(current, rng)
        if candidate and candidate != current:
            current = candidate
    return current
