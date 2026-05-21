"""Integration der `terminaltexteffects`-Library als Render-Effekt fuer Textual.

Public API:
    - `EFFECTS` - geordnete Liste (key, label) der unterstuetzten Effekte
    - `EFFECT_NONE` - reserved key fuer "kein Effekt"
    - `is_valid_effect(key)` - True wenn key ein bekannter Slug ist
    - `iter_effect_frames(text, key)` - liefert die Frame-Iteration eines tte-Effekts

Eigenheit von tte-Frames:
    Jeder Frame ist ein VOLLSTAENDIGER Text-Snapshot - reine ANSI-Farb-/Style-
    Codes plus die sichtbaren Zeichen, getrennt durch `\\n`. KEINE Cursor-
    Positionierungs-Sequenzen. Damit laesst sich jeder Frame direkt in ein
    Textual-Static-Widget rendern (z.B. via `Text.from_ansi`), ohne dass ein
    Mini-Terminal-Emulator gebraucht wird oder Textual suspended werden muss.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from importlib import import_module
from typing import Any

# Schluessel "none" ist reserviert fuer "kein Effekt" - der App-Code prueft das
# explizit, bevor sie einen Effekt startet.
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


# tte-Defaults sind fuer Desktop-Demos kalibriert - manche Effekte laufen
# 10-15 Sekunden, was sich in einer interaktiven TUI wie "haengt" anfuehlt.
# Hier kuerzen wir die Animationsdauer der bekannten Langläufer auf ein Mass,
# das zur Regenerate-Aktion passt. Werte sind effect_config-Felder.
_EFFECT_CONFIG_OVERRIDES: dict[str, dict[str, Any]] = {
    "matrix": {"rain_time": 2},  # Default 15s -> 2s
    "thunderstorm": {"storm_time": 3},  # Default 12s
    "vhstape": {"total_glitch_time": 120},  # Default 600 Frames
    "spotlights": {"search_duration": 180},  # Default 550 Frames
    "rings": {"disperse_duration": 80, "spin_duration": 80},  # Default 200/200
}


def iter_effect_frames(
    text: str,
    key: str,
    *,
    canvas_width: int = -1,
    canvas_height: int = -1,
) -> Iterator[str]:
    """Liefert die rohe Frame-Iteration eines tte-Effekts fuer Inline-Rendering.

    Args:
        text:
            Mehrzeiliger Text, der animiert werden soll. Jede Zeile ist
            eine eigene Vorschlags-Reihe.
        key:
            Effekt-Slug aus `EFFECTS`. `EFFECT_NONE` liefert einen leeren
            Iterator (kein Frame).
        canvas_width:
            Optionale Canvas-Breite in Zellen. -1 bedeutet "an den Text
            anpassen" (tte-Default). Werte > 0 zwingen tte, den Effekt
            ueber die volle Breite zu spielen - bewegungsbasierte Effekte
            (Matrix, Beams, Rain) profitieren davon, weil sie sonst nur
            in der schmalen Text-Spalte stattfinden.
        canvas_height:
            Analog fuer die Hoehe.

    Returns:
        Iterator ueber Frame-Strings. Jeder Frame ist ein vollstaendiger
        Text-Snapshot mit ANSI-Farb-/Style-Codes und `\\n` als Zeilentrenner -
        kompatibel mit `rich.text.Text.from_ansi(...)`.

    Bei unbekanntem `key` wird ein leerer Iterator zurueckgegeben.
    """
    if key == EFFECT_NONE:
        return iter(())
    for slug, _label, module_stem, class_name in _EFFECT_DEFS:
        if slug != key:
            continue
        effect_cls = _load_effect_class(module_stem, class_name)
        effect = effect_cls(text)
        if canvas_width > 0:
            effect.terminal_config.canvas_width = canvas_width
        if canvas_height > 0:
            effect.terminal_config.canvas_height = canvas_height
        # Text und Canvas zentrieren - so erscheint die Animation in der Mitte
        # des Panels statt unten-links angeklebt (tte-Default 'sw').
        effect.terminal_config.anchor_canvas = "c"
        effect.terminal_config.anchor_text = "c"
        for attr, value in _EFFECT_CONFIG_OVERRIDES.get(slug, {}).items():
            setattr(effect.effect_config, attr, value)
        return iter(effect)
    return iter(())
