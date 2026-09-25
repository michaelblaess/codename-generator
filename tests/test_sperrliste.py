"""Gesperrte Inhalte - bewusst entfernt, sie duerfen nicht zurueckkommen.

Swatch: Am 24.09.2026 entfernt. Die 97 Modellnamen sind Markenmaterial der
Swatch AG, fuer ein oeffentliches Werkzeug zu heikel (Michael: "die Swatch-Namen
sind zu heiss").

Whisky und Weine: Am 25.09.2026 entfernt. Die Brennereinamen sind eingetragene
Marken, viele Weinnamen geschuetzte Ursprungsbezeichnungen der EU. Die
Namen selbst stehen hier NICHT im Klartext - sonst laegen
sie wieder im oeffentlichen Repo. sperrliste_hashes.txt fuehrt SHA-256 ueber
den kleingeschriebenen Namen (casefold), dazu die Slugs der beiden Themes.
"Hermitage" bleibt erlaubt, das ist in den Wahrzeichen die Eremitage.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from codename_generator import wordlist
from codename_generator.wordlist import WordList, load_all_modifiers, load_themes

_GESPERRT = ("swatch",)
_DATA = Path(wordlist.__file__).parent / "data"
_HASH_DATEI = Path(__file__).parent / "sperrliste_hashes.txt"
_HASHES = frozenset(
    line.strip() for line in _HASH_DATEI.read_text(encoding="utf-8").splitlines() if line.strip()
)


def _alle_listen() -> list[WordList]:
    listen = list(load_themes().values())
    listen += [wl for pools in load_all_modifiers().values() for wl in pools.values()]
    return listen


def _hash(text: str) -> str:
    return hashlib.sha256(text.casefold().encode("utf-8")).hexdigest()


def test_keine_gesperrten_begriffe_in_den_daten() -> None:
    for path in _DATA.rglob("*.yaml"):
        text = path.read_text(encoding="utf-8").casefold()
        for begriff in _GESPERRT:
            assert begriff not in text, f"{begriff!r} steht wieder in {path.name}"


def test_kein_gesperrtes_thema_geladen() -> None:
    for liste in _alle_listen():
        felder = (liste.slug, liste.name, liste.description, *liste.words)
        for begriff in _GESPERRT:
            assert not any(begriff in feld.casefold() for feld in felder), liste.slug


def test_keine_gesperrten_namen_per_hash() -> None:
    assert len(_HASHES) > 200, "Sperrliste leer oder nicht gefunden"
    for liste in _alle_listen():
        for feld in (liste.slug, liste.name, *liste.words):
            assert _hash(feld) not in _HASHES, f"gesperrter Name in {liste.slug}: {feld!r}"
