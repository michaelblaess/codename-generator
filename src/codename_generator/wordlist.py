from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

_DATA_ROOT = Path(__file__).parent / "data"

# Sprache, die gilt wenn ein YAML kein `language` setzt. Auch der Fallback,
# wenn eine Sprache keine eigenen Modifier-Pools mitbringt.
DEFAULT_LANGUAGE = "en"

# Trennzeichen fuer das Genus eines Theme-Worts: "Falke|m". Nur Sprachen mit
# Adjektivflexion (Deutsch) brauchen das, alle anderen lassen es weg.
_GENDER_SEPARATOR = "|"
_VALID_GENDERS = frozenset({"m", "f", "n", "p"})


@dataclass(frozen=True)
class WordList:
    slug: str
    name: str
    description: str
    words: tuple[str, ...]
    # Optionale Theme-Overrides - leeres Tuple bedeutet "globalen Pool nutzen".
    adjectives: tuple[str, ...] = field(default_factory=tuple)
    verbs: tuple[str, ...] = field(default_factory=tuple)
    patterns: tuple[str, ...] = field(default_factory=tuple)
    # mutate: schaltet phonetische Mutation fuer dieses Theme ab wenn False.
    mutate: bool = True
    # default_mutation: Start-Mutationswert in Prozent beim Wechsel zum Theme.
    default_mutation: int | None = None
    # language: bestimmt die Modifier-Pools und die Flexionsregeln.
    language: str = DEFAULT_LANGUAGE
    # genders: parallel zu `words`, leerer String wenn ein Wort kein Genus hat.
    genders: tuple[str, ...] = field(default_factory=tuple)

    def gender_of(self, word: str) -> str:
        """Liefert das Genus eines Theme-Worts (leer wenn unbekannt)."""
        if not self.genders:
            return ""
        try:
            index = self.words.index(word)
        except ValueError:
            return ""
        return self.genders[index] if index < len(self.genders) else ""


def _load_yaml(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def _str_tuple(raw: object) -> tuple[str, ...]:
    """Konvertiert einen YAML-Wert in ein Tuple von Strings (leer wenn keine Liste)."""
    if not isinstance(raw, list):
        return ()
    return tuple(str(item) for item in raw)


@dataclass(frozen=True)
class _ParsedWords:
    words: tuple[str, ...]
    genders: tuple[str, ...]


def _split_gender(entry: str) -> tuple[str, str]:
    """Zerlegt einen Wort-Eintrag in Wort und Genus ("Falke|m" -> Falke, m)."""
    word, separator, gender = entry.partition(_GENDER_SEPARATOR)
    if not separator:
        return entry.strip(), ""
    marker = gender.strip().lower()
    return word.strip(), marker if marker in _VALID_GENDERS else ""


def _parse_words(raw: object, path: Path) -> _ParsedWords:
    """Liest die `words`-Liste inklusive optionaler Genus-Marker."""
    if not isinstance(raw, list):
        raise ValueError(f"'words' must be a list in {path}")
    pairs = [_split_gender(str(item)) for item in raw]
    return _ParsedWords(
        words=tuple(word for word, _ in pairs),
        genders=tuple(gender for _, gender in pairs) if any(g for _, g in pairs) else (),
    )


def _wordlist_from_path(path: Path, language: str = DEFAULT_LANGUAGE) -> WordList:
    data = _load_yaml(path)
    parsed = _parse_words(data.get("words", []), path)
    return WordList(
        slug=path.stem,
        name=str(data.get("name", path.stem)),
        description=str(data.get("description", "")),
        words=parsed.words,
        adjectives=_str_tuple(data.get("adjectives")),
        verbs=_str_tuple(data.get("verbs")),
        patterns=_str_tuple(data.get("patterns")),
        mutate=bool(data.get("mutate", True)),
        default_mutation=_optional_int(data.get("default_mutation")),
        language=str(data.get("language", language)),
        genders=parsed.genders,
    )


def _optional_int(raw: object) -> int | None:
    """Konvertiert einen YAML-Wert in int oder None."""
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    return None


def load_themes() -> dict[str, WordList]:
    """Lade alle Theme-Wortlisten aus data/themes/.

    Die Sprache steht im YAML (`language`), nicht im Pfad - Themes liegen
    weiterhin flach nebeneinander.
    """
    root = _DATA_ROOT / "themes"
    return {p.stem: _wordlist_from_path(p) for p in sorted(root.glob("*.yaml"))}


def available_languages() -> tuple[str, ...]:
    """Sprachen, fuer die eigene Modifier-Pools existieren (data/modifiers/<lang>/)."""
    root = _DATA_ROOT / "modifiers"
    return tuple(sorted(p.name for p in root.iterdir() if p.is_dir()))


def load_modifiers(language: str = DEFAULT_LANGUAGE) -> dict[str, WordList]:
    """Lade die Modifier-Wortlisten einer Sprache aus data/modifiers/<lang>/.

    Fehlt der Sprachordner, kommen die Pools der Default-Sprache zurueck.
    """
    root = _DATA_ROOT / "modifiers" / language
    if not root.is_dir():
        root = _DATA_ROOT / "modifiers" / DEFAULT_LANGUAGE
        language = DEFAULT_LANGUAGE
    return {p.stem: _wordlist_from_path(p, language) for p in sorted(root.glob("*.yaml"))}


def load_all_modifiers() -> dict[str, dict[str, WordList]]:
    """Lade die Modifier-Pools aller Sprachen, gebuendelt als Sprache -> Rolle."""
    return {language: load_modifiers(language) for language in available_languages()}
