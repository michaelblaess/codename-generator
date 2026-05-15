from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

_DATA_ROOT = Path(__file__).parent / "data"


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
    # bare: erlaubt nicht-mutierte Einzelwoerter als Vorschlag.
    bare: bool = False
    # mutate: schaltet phonetische Mutation fuer dieses Theme ab wenn False.
    mutate: bool = True


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


def _wordlist_from_path(path: Path) -> WordList:
    data = _load_yaml(path)
    words = data.get("words", [])
    if not isinstance(words, list):
        raise ValueError(f"'words' must be a list in {path}")
    return WordList(
        slug=path.stem,
        name=str(data.get("name", path.stem)),
        description=str(data.get("description", "")),
        words=tuple(str(w) for w in words),
        adjectives=_str_tuple(data.get("adjectives")),
        verbs=_str_tuple(data.get("verbs")),
        patterns=_str_tuple(data.get("patterns")),
        bare=bool(data.get("bare", False)),
        mutate=bool(data.get("mutate", True)),
    )


def load_themes() -> dict[str, WordList]:
    """Lade alle Theme-Wortlisten aus data/themes/."""
    root = _DATA_ROOT / "themes"
    return {p.stem: _wordlist_from_path(p) for p in sorted(root.glob("*.yaml"))}


def load_modifiers() -> dict[str, WordList]:
    """Lade alle Modifier-Wortlisten aus data/modifiers/."""
    root = _DATA_ROOT / "modifiers"
    return {p.stem: _wordlist_from_path(p) for p in sorted(root.glob("*.yaml"))}
