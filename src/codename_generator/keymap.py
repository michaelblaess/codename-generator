"""Tastenbelegung dieser Anwendung.

Die Mechanik (Stile, Vim-Ebene, eigene Belegungen, Pruefer) liegt in
`textual_widgets.keymap`, die Begruendung in textual-widgets/SHORTCUTS.md. Hier
steht nur, was codename-generator ausmacht: seine Aktionen im Bestandsstil,
die F-Tasten ab F7 und die Bruecke zu den Einstellungen. Vorbild ist
jira-timesheet (`jira_timesheet/keymap.py`).

Public API:
    - `CLASSIC` - die Belegung im Bestandsstil.
    - `LABELS` / `TOOLTIPS` - Beschriftung und Erklaerung je Aktion.
    - `APP_FUNCTION_KEYS` / `FUNCTION_KEYS` - die F-Tasten dieser Anwendung.
    - `resolve(settings)` - die fertige Belegung aus dem Settings-Dict.
    - `style_from_settings(settings)` - der gewaehlte oder vorgeschlagene Stil.
    - `key_display(key)` - die Anzeige einer Taste im Footer.
"""

from __future__ import annotations

from collections.abc import Mapping

from textual_widgets.keymap import (
    COMMON_FUNCTION_KEYS,
    KeyBinding,
    KeymapStyle,
    ResolvedKeymap,
    default_style_for_platform,
    parse_overrides,
    resolve_keymap,
    sort_for_footer,
)

CLASSIC: dict[str, KeyBinding] = {
    "regenerate": KeyBinding(("r", "R")),
    "copy_name": KeyBinding(("n", "N")),
    # Slug kopieren geht auch ueber das Kontextmenue - im Footer nur Ballast.
    "copy_slug": KeyBinding(("c", "C"), show=False),
    "toggle_favorite": KeyBinding(("f", "F")),
    # Die Favoriten stehen als erster Eintrag in der Themenliste.
    "open_favorites": KeyBinding(("v", "V"), show=False),
    "add_custom_favorite": KeyBinding(("plus",)),
    # Eigenes Wort auf o ("own word"). Bis v0.4.0 lag es auf i - das ist in
    # allen anderen TUIs die Info, die Konvention hat Vorrang.
    "edit_seed": KeyBinding(("o", "O")),
    "vary_word": KeyBinding(("w", "W")),
    # m ("modifier") statt k: k ist eine Vim-Taste und waere mit
    # eingeschalteter Vim-Navigation stumm, solange die Tabelle den Fokus hat.
    "vary_modifier": KeyBinding(("m", "M")),
    # Mutation +25 % zog dafuer von m auf u. Der Regler steht daneben.
    "bump_mutation": KeyBinding(("u", "U"), show=False),
    "cycle_language": KeyBinding(("l", "L")),
    # Das Farbthema geht auch ueber Ctrl+P.
    "cycle_theme": KeyBinding(("t", "T"), show=False),
    "show_settings": KeyBinding(("s", "S")),
    "show_about": KeyBinding(("i", "I")),
    "keymap_overview": KeyBinding(("question_mark",), show=False),
    "quit": KeyBinding(("q", "Q")),
}
"""Der Bestandsstil. Reihenfolge = Reihenfolge im Footer."""

LABELS: dict[str, str] = {
    "regenerate": "Regenerate",
    "copy_name": "Copy name",
    "copy_slug": "Copy slug",
    "toggle_favorite": "Fav",
    "open_favorites": "View favs",
    "add_custom_favorite": "Add idea",
    "edit_seed": "Own word",
    "vary_word": "Keep word",
    "vary_modifier": "Keep mod",
    "bump_mutation": "Mutation +25%",
    "cycle_language": "Language",
    "cycle_theme": "Theme",
    "show_settings": "Settings",
    "show_about": "Info",
    "keymap_overview": "Keys",
    "quit": "Quit",
}
"""Footer-Beschriftung je Aktion. Die Oberflaeche der TUI ist englisch."""

TOOLTIPS: dict[str, str] = {
    "regenerate": "Roll a fresh batch for the current view",
    "copy_name": "Copy the highlighted name to the clipboard",
    "copy_slug": "Copy the slug of the highlighted name (folders, URLs)",
    "toggle_favorite": "Keep the highlighted name - or drop it again",
    "open_favorites": "Show your favorites",
    "add_custom_favorite": "Add a name of your own to the favorites",
    "edit_seed": "Enter your own word and combine it with modifiers or a theme",
    "vary_word": "Keep the word of the highlighted name, roll new modifiers",
    "vary_modifier": "Keep the modifier of the highlighted name, swap the word",
    "bump_mutation": "Raise the mutation chance by 25 %",
    "cycle_language": "Switch the language of the generated names",
    "cycle_theme": "Switch the colour theme",
    "show_settings": "Keyboard layout and where your data is stored",
    "show_about": "Version, author and licence",
    "keymap_overview": "Show every key that is bound right now",
    "quit": "Quit codename-generator",
}
"""Footer-Tooltip je Aktion - ein ganzer Satz, nicht das Label wiederholt."""

APP_FUNCTION_KEYS: dict[str, KeyBinding] = {
    "regenerate": KeyBinding(("f5", "r", "R")),
    "edit_seed": KeyBinding(("f7", "o", "O")),
    "vary_word": KeyBinding(("f8", "w", "W")),
    "vary_modifier": KeyBinding(("f9", "m", "M")),
    "cycle_language": KeyBinding(("f10", "l", "L")),
}
"""Die F-Tasten, die diese Anwendung selbst vergibt.

`f1`, `f2` und `quit` kommen aus der gemeinsamen Konvention. F5 ist dort
"Aktualisieren" - hier heisst das: neuer Stapel. Ab F7 die vier Schritte der
Namenssuche: eigenes Wort, Wort halten, Zusatz halten, Sprache. F10 bedeutet
damit in jeder Anwendung etwas anderes (jira-timesheet: Export), das steht als
offener Punkt in SHORTCUTS.md.

`l` behaelt die Sprache neben F10. Mit eingeschalteter Vim-Navigation ist `l`
stumm, solange die Tabelle den Fokus hat - der Pruefer meldet das ins Log, und
F10 bleibt erreichbar.
"""

FUNCTION_KEYS: dict[str, KeyBinding] = {**COMMON_FUNCTION_KEYS, **APP_FUNCTION_KEYS}
"""Die gemeinsame Konvention plus die Ergaenzungen dieser Anwendung."""

KEY_DISPLAY: dict[str, str] = {
    "plus": "+",
    "question_mark": "?",
    **{f"f{n}": f"F{n}" for n in range(1, 11)},
}


def key_display(key: str) -> str:
    """Uebersetzt einen Tastennamen in seine Anzeige im Footer.

    Args:
        key: Der Tastenname, so wie Textual ihn kennt.

    Returns:
        Der Text fuer den Footer.
    """
    return KEY_DISPLAY.get(key, key)


def style_from_settings(settings: Mapping[str, object]) -> KeymapStyle:
    """Ermittelt den Stil aus den Einstellungen.

    Ein leerer Wert heisst "noch nicht entschieden" - dann entscheidet die
    Plattform, damit eine frische Installation auf dem Mac nicht mit F-Tasten
    startet, die das Betriebssystem abfaengt.

    Args:
        settings: Das geladene Settings-Dict.

    Returns:
        Der anzuwendende Stil.
    """
    gewaehlt = str(settings.get("keymap_style", "") or "").strip().lower()
    for stil in KeymapStyle:
        if gewaehlt == stil.value:
            return stil
    return default_style_for_platform()


def resolve(settings: Mapping[str, object]) -> ResolvedKeymap:
    """Baut die fertige Belegung aus den Einstellungen.

    Im F-Tasten-Stil nach F-Nummer sortiert, im Bestandsstil in der
    Reihenfolge von `CLASSIC` - wie in jira-timesheet.

    Args:
        settings: Das geladene Settings-Dict.

    Returns:
        Die Belegung samt Beanstandungen fuer das Log.
    """
    stil = style_from_settings(settings)
    overrides, probleme = parse_overrides(settings.get("keymap_custom"))
    ergebnis = resolve_keymap(
        stil,
        CLASSIC,
        function_keys=FUNCTION_KEYS,
        overrides=overrides,
        vim_navigation=bool(settings.get("keymap_vim", False)),
    )
    bindings = (
        sort_for_footer(ergebnis.bindings)
        if stil is KeymapStyle.FUNCTION_KEYS
        else dict(ergebnis.bindings)
    )
    return ResolvedKeymap(bindings=bindings, problems=probleme + ergebnis.problems)
