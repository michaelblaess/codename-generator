"""Favoriten lesen, schreiben und zwischen TUI und Web austauschen.

Das Format ist in beiden Fassungen dasselbe: eine Liste von Eintraegen mit
name, slug, pattern, mutated und source_words. Eine Austauschdatei traegt die
Liste unter "favorites" - genau wie die settings.json der TUI. Deshalb laesst
sich eine settings.json auch direkt importieren.
"""

from __future__ import annotations

import json
from pathlib import Path

from codename_generator.generator import Pattern, Suggestion

EXPORT_KEY = "favorites"


def favorite_to_dict(favorite: Suggestion) -> dict[str, object]:
    return {
        "name": favorite.name,
        "slug": favorite.slug,
        "pattern": favorite.pattern.value,
        "mutated": favorite.mutated,
        "source_words": list(favorite.source_words),
    }


def favorite_from_dict(item: object) -> Suggestion | None:
    """Ein gespeicherter Eintrag als Suggestion - None, wenn er unvollstaendig ist."""
    if not isinstance(item, dict):
        return None
    try:
        words = item["source_words"]
        if not isinstance(words, list):
            return None
        return Suggestion(
            name=str(item["name"]),
            slug=str(item["slug"]),
            pattern=Pattern(str(item["pattern"])),
            mutated=bool(item.get("mutated", False)),
            source_words=tuple(str(w) for w in words),
        )
    except (KeyError, ValueError, TypeError):
        return None


def parse_favorites(raw: object) -> list[Suggestion]:
    """Liest eine Liste oder ein Dokument mit "favorites" - unbrauchbare Eintraege fallen weg."""
    if isinstance(raw, dict):
        raw = raw.get(EXPORT_KEY)
    if not isinstance(raw, list):
        return []
    parsed = (favorite_from_dict(item) for item in raw)
    return [favorite for favorite in parsed if favorite is not None]


def merge_favorites(
    existing: list[Suggestion], incoming: list[Suggestion]
) -> tuple[list[Suggestion], int]:
    """Haengt neue Favoriten an, ein Slug, der schon da ist, bleibt einmal. Liefert (Liste, neu)."""
    slugs = {favorite.slug for favorite in existing}
    merged = list(existing)
    for favorite in incoming:
        if favorite.slug in slugs:
            continue
        slugs.add(favorite.slug)
        merged.append(favorite)
    return merged, len(merged) - len(existing)


def export_document(favorites: list[Suggestion]) -> dict[str, object]:
    return {EXPORT_KEY: [favorite_to_dict(f) for f in favorites]}


def write_export(path: Path, favorites: list[Suggestion]) -> None:
    text = json.dumps(export_document(favorites), indent=2, ensure_ascii=False)
    path.write_text(f"{text}\n", encoding="utf-8")


def read_import(path: Path) -> list[Suggestion]:
    """Liest eine Austauschdatei. Kaputtes JSON ist ein Fehler, kein leerer Import."""
    return parse_favorites(json.loads(path.read_text(encoding="utf-8")))
