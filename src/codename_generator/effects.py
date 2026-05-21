"""Integration der `terminaltexteffects`-Library als optionaler Render-Effekt.

Public API:
    - `EFFECTS` - geordnete Liste (key, label) der unterstuetzten Effekte
    - `EFFECTS_BY_KEY` - Dict key -> tte-Effekt-Klasse
    - `play_effect(text, key)` - spielt den gewaehlten Effekt direkt im Terminal

`terminaltexteffects` schreibt rohe ANSI-Sequenzen (inkl. Cursor-Positionierung)
direkt nach stdout. Das vertraegt sich nicht mit Textuals Compositor; der
Aufrufer muss `App.suspend()` als Kontextmanager um `play_effect()` legen,
damit Textual fuer die Dauer der Animation aus dem Terminal raus ist.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module
from typing import Any

# Schluessel "none" ist reserviert fuer "kein Effekt" - der App-Code prueft das
# explizit, bevor sie play_effect aufruft.
EFFECT_NONE = "none"

# (key, label, modul, klasse)
# Reihenfolge bestimmt die Reihenfolge im Dropdown - alphabetisch ueber alle
# tte-Effekte aus terminaltexteffects 0.15.0.
_EFFECT_DEFS: tuple[tuple[str, str, str, str], ...] = (
    ("beams", "Beams", "effect_beams", "Beams"),
    ("binarypath", "BinaryPath", "effect_binarypath", "BinaryPath"),
    ("blackhole", "Blackhole", "effect_blackhole", "Blackhole"),
    ("bouncyballs", "BouncyBalls", "effect_bouncyballs", "BouncyBalls"),
    ("bubbles", "Bubbles", "effect_bubbles", "Bubbles"),
    ("burn", "Burn", "effect_burn", "Burn"),
    ("colorshift", "ColorShift", "effect_colorshift", "ColorShift"),
    ("crumble", "Crumble", "effect_crumble", "Crumble"),
    ("decrypt", "Decrypt", "effect_decrypt", "Decrypt"),
    ("errorcorrect", "ErrorCorrect", "effect_errorcorrect", "ErrorCorrect"),
    ("expand", "Expand", "effect_expand", "Expand"),
    ("fireworks", "Fireworks", "effect_fireworks", "Fireworks"),
    ("highlight", "Highlight", "effect_highlight", "Highlight"),
    ("laseretch", "LaserEtch", "effect_laseretch", "LaserEtch"),
    ("matrix", "Matrix", "effect_matrix", "Matrix"),
    ("middleout", "MiddleOut", "effect_middleout", "MiddleOut"),
    ("orbittingvolley", "OrbittingVolley", "effect_orbittingvolley", "OrbittingVolley"),
    ("overflow", "Overflow", "effect_overflow", "Overflow"),
    ("pour", "Pour", "effect_pour", "Pour"),
    ("print", "Print", "effect_print", "Print"),
    ("rain", "Rain", "effect_rain", "Rain"),
    ("random_sequence", "RandomSequence", "effect_random_sequence", "RandomSequence"),
    ("rings", "Rings", "effect_rings", "Rings"),
    ("scattered", "Scattered", "effect_scattered", "Scattered"),
    ("slice", "Slice", "effect_slice", "Slice"),
    ("slide", "Slide", "effect_slide", "Slide"),
    ("smoke", "Smoke", "effect_smoke", "Smoke"),
    ("spotlights", "Spotlights", "effect_spotlights", "Spotlights"),
    ("spray", "Spray", "effect_spray", "Spray"),
    ("swarm", "Swarm", "effect_swarm", "Swarm"),
    ("sweep", "Sweep", "effect_sweep", "Sweep"),
    ("synthgrid", "SynthGrid", "effect_synthgrid", "SynthGrid"),
    ("thunderstorm", "Thunderstorm", "effect_thunderstorm", "Thunderstorm"),
    ("unstable", "Unstable", "effect_unstable", "Unstable"),
    ("vhstape", "VHSTape", "effect_vhstape", "VHSTape"),
    ("waves", "Waves", "effect_waves", "Waves"),
    ("wipe", "Wipe", "effect_wipe", "Wipe"),
)


def _load_effect_class(module_stem: str, class_name: str) -> Callable[[str], Any]:
    """Lazy-Loader: importiert die Effekt-Klasse beim ersten Aufruf."""
    module = import_module(f"terminaltexteffects.effects.{module_stem}")
    cls = getattr(module, class_name)
    return cls  # type: ignore[no-any-return]


# Dropdown-Eintraege (key, label). "none" steht zuerst.
EFFECTS: tuple[tuple[str, str], ...] = (
    (EFFECT_NONE, "Kein Effekt"),
    *((key, label) for key, label, _mod, _cls in _EFFECT_DEFS),
)

# Schluessel-Set fuer die Validierung beim Laden aus den Settings.
_VALID_KEYS = frozenset(key for key, _ in EFFECTS)


def is_valid_effect(key: str) -> bool:
    """True, wenn `key` ein bekannter Effekt-Slug (inkl. "none") ist."""
    return key in _VALID_KEYS


def play_effect(text: str, key: str) -> None:
    """Spielt den gewaehlten Effekt auf `text` im aktuellen Terminal.

    Args:
        text:
            Mehrzeiliger Text, der animiert werden soll. Jede Zeile ist
            eine eigene Vorschlags-Reihe.
        key:
            Effekt-Slug aus `EFFECTS`. `EFFECT_NONE` ist ein No-op.

    Wichtig:
        Der Aufrufer muss `App.suspend()` aussenrum legen, damit Textual
        das Terminal freigibt. Ohne Suspend kollidiert tte mit Textuals
        Compositor und rendert kaputt.
    """
    if key == EFFECT_NONE:
        return
    for slug, _label, module_stem, class_name in _EFFECT_DEFS:
        if slug != key:
            continue
        effect_cls = _load_effect_class(module_stem, class_name)
        effect = effect_cls(text)
        with effect.terminal_output() as terminal:
            for frame in effect:
                terminal.print(frame)
        return
    # Unbekannter Key - still ignorieren statt zu crashen.
