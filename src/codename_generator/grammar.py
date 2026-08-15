"""Sprachabhaengige Wortformen.

Englisch stellt Modifier unveraendert voran ("Swift Falcon"). Deutsch flektiert
ein vorangestelltes Adjektiv nach dem Genus des Nomens - ohne das kommt
"Schnell Falke" heraus statt "Schneller Falke".
"""

from __future__ import annotations

GERMAN = "de"

# Starke Deklination, Nominativ Singular, ohne Artikel: der schnelle -> schneller
# Falke, die schnelle Mamba, das schnelle Rudel, die schnellen (p) Woelfe.
_GERMAN_ENDINGS: dict[str, str] = {
    "m": "er",
    "f": "e",
    "n": "es",
    "p": "e",
}

# Genus, das gilt wenn ein deutsches Theme sein Wort ohne Marker fuehrt.
_GERMAN_FALLBACK_GENDER = "m"


def _german_stem(word: str) -> str:
    """Tilgt das e in Stammendungen auf -el (dunkel -> dunkl, edel -> edl)."""
    return f"{word[:-2]}l" if word.endswith("el") else word


def inflect_attribute(word: str, gender: str, language: str) -> str:
    """Beugt einen vorangestellten Modifier fuer die jeweilige Sprache.

    Sprachen ohne Flexionsregel (Default: Englisch) geben das Wort unveraendert
    zurueck. Fuer Deutsch entscheidet das Genus des Nomens ueber die Endung, ein
    fehlender Marker wird als Maskulinum behandelt.
    """
    if language != GERMAN or not word:
        return word
    ending = _GERMAN_ENDINGS.get(gender or _GERMAN_FALLBACK_GENDER, "")
    if not ending:
        return word
    # Ein Stamm, der bereits auf e endet ("leise"), bekommt nur den Rest.
    if word.endswith("e"):
        return f"{word}{ending[1:]}" if ending.startswith("e") else f"{word}{ending}"
    return f"{_german_stem(word)}{ending}"
