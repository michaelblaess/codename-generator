"""Gesperrte Inhalte - bewusst entfernt, sie duerfen nicht zurueckkommen.

Swatch: Am 24.09.2026 entfernt. Die 97 Modellnamen sind Markenmaterial der
Swatch AG, fuer ein oeffentliches Werkzeug zu heikel (Michael: "die Swatch-Namen
sind zu heiss"). Der Test prueft Dateien, Namen, Beschreibungen und Woerter.
"""

from __future__ import annotations

from pathlib import Path

import codename_generator
from codename_generator.wordlist import load_all_modifiers, load_themes

_GESPERRT = ("swatch",)
_DATA = Path(codename_generator.__file__).parent / "data"


def test_keine_gesperrten_begriffe_in_den_daten() -> None:
    for path in _DATA.rglob("*.yaml"):
        text = path.read_text(encoding="utf-8").casefold()
        for begriff in _GESPERRT:
            assert begriff not in text, f"{begriff!r} steht wieder in {path.name}"


def test_kein_gesperrtes_thema_geladen() -> None:
    lists = list(load_themes().values())
    lists += [wl for pools in load_all_modifiers().values() for wl in pools.values()]
    for wordlist in lists:
        felder = (wordlist.slug, wordlist.name, wordlist.description, *wordlist.words)
        for begriff in _GESPERRT:
            assert not any(begriff in feld.casefold() for feld in felder), wordlist.slug
