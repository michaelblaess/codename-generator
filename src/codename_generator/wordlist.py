from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

_DATA_ROOT = Path(__file__).parent / "data"


@dataclass(frozen=True)
class WordList:
    slug: str
    name: str
    description: str
    words: tuple[str, ...]


def _load_yaml(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


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
    )


def load_themes() -> dict[str, WordList]:
    """Lade alle Theme-Wortlisten aus data/themes/."""
    root = _DATA_ROOT / "themes"
    return {p.stem: _wordlist_from_path(p) for p in sorted(root.glob("*.yaml"))}


def load_modifiers() -> dict[str, WordList]:
    """Lade alle Modifier-Wortlisten aus data/modifiers/."""
    root = _DATA_ROOT / "modifiers"
    return {p.stem: _wordlist_from_path(p) for p in sorted(root.glob("*.yaml"))}
