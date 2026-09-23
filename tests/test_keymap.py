"""Tastenbelegung nach textual_widgets.keymap - Tabelle und Aufloesung."""

from __future__ import annotations

import pytest
from textual_widgets.keymap import KeymapStyle, find_collisions

from codename_generator import keymap
from codename_generator.tui import CodenameApp


@pytest.mark.parametrize("style", ["classic", "function_keys"])
def test_beide_stile_ohne_kollision(style: str) -> None:
    resolved = keymap.resolve({"keymap_style": style})
    assert resolved.problems == ()
    assert find_collisions(resolved.bindings) == ()


def test_jede_aktion_hat_methode_beschriftung_und_tooltip() -> None:
    for action in keymap.CLASSIC:
        if action != "quit":
            assert hasattr(CodenameApp, f"action_{action}"), action
        assert action in keymap.LABELS, action
        assert action in keymap.TOOLTIPS, action


def test_konvention_i_ist_info_und_s_sind_einstellungen() -> None:
    classic = keymap.resolve({"keymap_style": "classic"}).bindings
    assert "i" in classic["show_about"].keys
    assert "s" in classic["show_settings"].keys
    assert "o" in classic["edit_seed"].keys


def test_f_tasten_stil_sortiert_und_belegt() -> None:
    bindings = keymap.resolve({"keymap_style": "function_keys"}).bindings
    assert bindings["show_about"].keys[0] == "f1"
    assert bindings["show_settings"].keys[0] == "f2"
    assert bindings["regenerate"].keys[:2] == ("f5", "r")
    assert list(bindings)[:2] == ["show_about", "show_settings"]


def test_vim_verdeckt_nur_die_sprache() -> None:
    """k lag bis v0.4 auf Zusatz halten - mit Vim waere das stumm gewesen."""
    for style in ("classic", "function_keys"):
        problems = keymap.resolve({"keymap_style": style, "keymap_vim": True}).problems
        assert {p.action for p in problems} == {"cycle_language"}, problems


def test_leerer_stil_folgt_der_plattform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.platform", "darwin")
    assert keymap.style_from_settings({}) is KeymapStyle.CLASSIC


def test_eigene_belegung_wirkt_und_unbekanntes_wird_gemeldet() -> None:
    resolved = keymap.resolve(
        {"keymap_style": "classic", "keymap_custom": {"regenerate": ["x"], "gibtsnicht": ["y"]}}
    )
    assert resolved.bindings["regenerate"].keys == ("x",)
    assert any(p.action == "gibtsnicht" for p in resolved.problems)
