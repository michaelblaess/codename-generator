"""Filter und Klangbewertung fuer fertige Namen.

Alles hier ist deterministisch und laeuft auf dem gerenderten Namen - also
nach Mutation und Wortzahl, so wie ihn der Benutzer sieht. Die Regeln sind
bewusst einfach gehalten und in den Testvektoren festgeschrieben, damit der
TypeScript-Port dieselben Zahlen liefert.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

_VOWELS = frozenset("aeiouyäöüàáâéèêíìîóòôúùû")
_ASCII_LETTERS = frozenset("abcdefghijklmnopqrstuvwxyz")
# Mehrbuchstabige Laute, die beim Zaehlen von Konsonantenhaeufungen als einer
# gelten - "sch" in "Schmied" ist kein Dreierhaufen.
_DIGRAPHS = ("sch", "ch", "ck", "sh", "th", "ph")
_DIGRAPH_PLACEHOLDER = "C"

SCORE_MAX = 100


def _letters(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalpha())


def _is_vowel(word: str, index: int) -> bool:
    """Ein y am Wortanfang ist Konsonant ("Yarrow"), sonst Vokal ("Pyro")."""
    ch = word[index]
    return ch in _VOWELS and not (ch == "y" and index == 0)


def count_syllables(word: str, language: str) -> int:
    """Silben eines Worts, geschaetzt ueber Vokalgruppen.

    Im Englischen zaehlt ein stummes End-e nicht mit ("blade"), ausser nach
    l ("table"). Die Schaetzung irrt bei Einzelfaellen wie "Orion", reicht aber
    fuer einen Filter "hoechstens drei Silben".
    """
    letters = _letters(word)
    if not letters:
        return 0
    groups = 0
    previous = False
    for index in range(len(letters)):
        vowel = _is_vowel(letters, index)
        if vowel and not previous:
            groups += 1
        previous = vowel
    if (
        language == "en"
        and len(letters) > 3
        and letters.endswith("e")
        and not letters.endswith("le")
        and letters[-2] not in _VOWELS
        and groups > 1
    ):
        groups -= 1
    return max(1, groups)


def name_syllables(name: str, language: str) -> int:
    """Silben eines ganzen Namens (Summe ueber seine Woerter)."""
    return sum(count_syllables(word, language) for word in name.split())


def is_alliteration(name: str) -> bool:
    """Beginnen alle Woerter mit demselben Buchstaben? Ein einzelnes Wort zaehlt nicht."""
    words = name.split()
    if len(words) < 2:
        return False
    initials = {word[:1].lower() for word in words}
    return len(initials) == 1


def _cluster_penalty(word: str) -> int:
    """8 Punkte je Haeufung von drei oder mehr Konsonanten ("Strkt")."""
    simplified = word.lower()
    for digraph in _DIGRAPHS:
        simplified = simplified.replace(digraph, _DIGRAPH_PLACEHOLDER)
    penalty = 0
    run = 0
    for index, ch in enumerate(simplified):
        if ch.isalpha() and not _is_vowel(simplified, index):
            run += 1
            if run == 3:
                penalty += 8
        else:
            run = 0
    return penalty


def sound_score(name: str, language: str) -> int:
    """Klangwert 0-100: kurz, gut sprechbar und leicht zu buchstabieren gewinnt.

    Abzuege gibt es fuer zu wenige oder zu viele Silben, fuer eine Laenge
    ausserhalb von 5-12 Buchstaben, fuer Konsonantenhaeufungen, fuer Zeichen
    ausserhalb von a-z (Umlaute stoeren in Domains und beim Tippen), fuer
    mehrdeutige Schreibungen (q, x, ph) und doppelte Buchstaben, und fuer drei
    Woerter. Eine Alliteration bringt einen Bonus.
    """
    words = name.split()
    letters = _letters(name)
    if not letters:
        return 0
    score = SCORE_MAX
    syllables = name_syllables(name, language)
    if syllables <= 1 or syllables == 5:
        score -= 10
    elif syllables > 5:
        score -= 20 + 5 * (syllables - 6)
    length = len(letters)
    if length < 5:
        score -= 3 * (5 - length)
    elif length > 12:
        score -= min(25, 3 * (length - 12))
    for word in words:
        score -= _cluster_penalty(word)
        lowered = word.lower()
        score -= 3 * lowered.count("ph")
        doubles = sum(1 for a, b in pairwise(lowered) if a == b and a.isalpha())
        score -= 2 * doubles
    score -= 6 * sum(1 for ch in letters if ch not in _ASCII_LETTERS)
    score -= 3 * sum(1 for ch in letters if ch in "qx")
    if len(words) >= 3:
        score -= 5
    if is_alliteration(name):
        score += 5
    return max(0, min(SCORE_MAX, score))


@dataclass(frozen=True)
class NameFilter:
    """Was ein Name erfuellen muss, um angezeigt zu werden. Leer = alles."""

    initial: str = ""
    max_syllables: int = 0
    alliteration: bool = False

    @property
    def active(self) -> bool:
        return bool(self.initial or self.max_syllables or self.alliteration)


def matches(name: str, name_filter: NameFilter, language: str) -> bool:
    """Prueft einen gerenderten Namen gegen den Filter."""
    if name_filter.initial and not name.lower().startswith(name_filter.initial.lower()):
        return False
    if name_filter.max_syllables and name_syllables(name, language) > name_filter.max_syllables:
        return False
    return not (name_filter.alliteration and not is_alliteration(name))
