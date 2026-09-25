"""Neue Woerter aus einem Theme: Kunstwoerter (Silbenmodell) und Kofferwoerter.

Beide Verfahren sind so gebaut, dass der TypeScript-Port in codename-generator.de
exakt dasselbe liefert: das Kunstwort fragt den Zufall nur ueber `choice` (das
Drehbuch der Testvektoren greift dort), das Kofferwort braucht gar keinen Zufall.
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

# Markierungen fuer Wortanfang und -ende im Buchstabenmodell. Beide sortieren
# vor jedem Buchstaben - die Reihenfolge der Uebergaenge ist damit in Python
# und JavaScript dieselbe.
_START = "^"
_END = "$"
_ORDER = 2

COIN_MIN_LENGTH = 4
COIN_MAX_LENGTH = 10
# Ein Quellwort, das so lang ist, darf nicht als Ganzes im Kunstwort stecken -
# "Andromedaris" ist kein neues Wort, sondern ein altes mit Anhang.
_EMBEDDED_MIN_LENGTH = 4

_BLEND_VOWELS = frozenset("aeiouyäöü")
_BLEND_MIN_LENGTH = 4
# Kofferwoerter zielen auf hoechstens acht Buchstaben - lange Quellwoerter
# ("Kilimanjaro") ergaeben sonst Ungetueme, die keiner aussprechen mag.
_BLEND_TARGET_MAX = 8


def coin_tokens(words: Iterable[str]) -> tuple[str, ...]:
    """Einzelwoerter eines Themes als Trainingsmaterial: klein, nur Buchstaben, ab 3 Zeichen.

    Mehrteilige Eintraege ("Ursa Major") zaehlen als zwei Woerter.
    """
    seen: dict[str, None] = {}
    for word in words:
        for token in word.replace("-", " ").split():
            lowered = token.lower()
            if len(lowered) >= 3 and lowered.isalpha():
                seen.setdefault(lowered, None)
    return tuple(seen)


@dataclass(frozen=True)
class CoinModel:
    """Buchstabenmodell zweiter Ordnung: welcher Buchstabe folgt auf welches Paar.

    Die Folgebuchstaben stehen sortiert und mit Wiederholung in der Liste - ein
    Buchstabe, der dreimal folgt, steht dreimal darin. So ist `choice` gleich
    eine gewichtete Wahl.
    """

    tokens: tuple[str, ...]
    transitions: dict[str, tuple[str, ...]]

    @classmethod
    def from_words(cls, words: Iterable[str]) -> CoinModel:
        tokens = coin_tokens(words)
        followers: dict[str, list[str]] = {}
        for token in tokens:
            padded = f"{_START * _ORDER}{token}{_END}"
            for index in range(_ORDER, len(padded)):
                followers.setdefault(padded[index - _ORDER : index], []).append(padded[index])
        return cls(tokens=tokens, transitions={k: tuple(sorted(v)) for k, v in followers.items()})


def coin_word(model: CoinModel, rng: random.Random) -> str | None:
    """Ein Versuch fuer ein Kunstwort - None, wenn er nichts Brauchbares ergibt.

    Verworfen wird, was zu kurz oder zu lang ist, was nur ein Stueck eines
    echten Worts ist ("lagavu") und was ein echtes Wort ganz enthaelt.
    """
    state = _START * _ORDER
    letters: list[str] = []
    while True:
        options = model.transitions.get(state)
        if not options:
            return None
        letter = rng.choice(options)
        if letter == _END:
            break
        letters.append(letter)
        if len(letters) > COIN_MAX_LENGTH:
            return None
        state = f"{state[1:]}{letter}"
    word = "".join(letters)
    if len(word) < COIN_MIN_LENGTH:
        return None
    for token in model.tokens:
        if word in token:
            return None
        if len(token) >= _EMBEDDED_MIN_LENGTH and token in word:
            return None
    return f"{word[:1].upper()}{word[1:]}"


def coin_words(model: CoinModel, rng: random.Random, count: int) -> list[str]:
    """Bis zu `count` verschiedene Kunstwoerter (weniger, wenn das Modell zu klein ist)."""
    result: list[str] = []
    seen: set[str] = set()
    attempts = 0
    max_attempts = count * 60
    while model.tokens and len(result) < count and attempts < max_attempts:
        attempts += 1
        word = coin_word(model, rng)
        if word is None or word.lower() in seen:
            continue
        seen.add(word.lower())
        result.append(word)
    return result


def blendable(word: str) -> bool:
    """Taugt ein Theme-Wort fuer ein Kofferwort? Nur einteilige Woerter aus Buchstaben."""
    return len(word) >= 3 and word.isalpha()


def _edit_distance(a: str, b: str) -> int:
    """Levenshtein-Abstand - wie viele Buchstaben einfuegen, loeschen oder tauschen."""
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def blend(first: str, second: str) -> str | None:
    """Verschmilzt zwei Woerter an einem gemeinsamen Buchstaben ("Orion" + "Andromeda").

    Vom ersten Wort bleibt der Anfang bis zu einem Buchstaben, den auch das
    zweite hat, vom zweiten der Rest ab dort: "Oro" + "meda" = "Oromeda". Unter
    allen Nahtstellen gewinnt die, deren Laenge am naechsten am Mittel beider
    Woerter liegt (hoechstens acht), bei Gleichstand eine Naht auf einem Vokal, dann die mit mehr
    vom ersten Wort. Was nur einen Buchstaben von einem der beiden Woerter
    abweicht, zaehlt nicht. Keine Naht, kein Kofferwort.
    """
    a = first.lower()
    b = second.lower()
    if not (blendable(a) and blendable(b)) or a == b:
        return None
    target = max(5, min(_BLEND_TARGET_MAX, (len(a) + len(b) + 1) // 2))
    best: tuple[tuple[int, int, int, int], str] | None = None
    for i in range(2, len(a)):
        for j in range(1, len(b) - 1):
            if a[i - 1] != b[j - 1]:
                continue
            word = f"{a[:i]}{b[j:]}"
            if not _BLEND_MIN_LENGTH <= len(word) <= COIN_MAX_LENGTH or a in word or b in word:
                continue
            # Ein Buchstabe Unterschied ist keine Verschmelzung, sondern eine
            # Kopie: Orion + Arcturus ergab "Orcturus".
            if _edit_distance(word, a) <= 1 or _edit_distance(word, b) <= 1:
                continue
            key = (abs(len(word) - target), 0 if a[i - 1] in _BLEND_VOWELS else 1, -i, j)
            if best is None or key < best[0]:
                best = (key, word)
    if best is None:
        return None
    word = best[1]
    return f"{word[:1].upper()}{word[1:]}"


def blend_pairs(
    firsts: Sequence[str], seconds: Sequence[str], rng: random.Random, count: int
) -> list[tuple[str, str, str]]:
    """Zufaellige Paare samt Kofferwort: (erstes Wort, zweites Wort, Kofferwort).

    Jedes Kofferwort hoechstens einmal. Kommen beide Seiten aus demselben
    Theme, wird kein Wort mit sich selbst verschmolzen.
    """
    left = [w for w in firsts if blendable(w)]
    right = [w for w in seconds if blendable(w)]
    result: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    attempts = 0
    max_attempts = count * 60
    while left and right and len(result) < count and attempts < max_attempts:
        attempts += 1
        a = rng.choice(left)
        b = rng.choice(right)
        if a.lower() == b.lower():
            continue
        word = blend(a, b)
        if word is None or word.lower() in seen:
            continue
        seen.add(word.lower())
        result.append((a, b, word))
    return result
