from __future__ import annotations

import os
import subprocess
import sys

from codename_generator.cli import DEFAULT_MUTATION_CHANCE, _mutation_chance


def test_explicit_value_wins() -> None:
    assert _mutation_chance(0, 0.9) == 0.9


def test_theme_default_beats_global_default() -> None:
    assert _mutation_chance(0, None) == 0.0
    assert _mutation_chance(25, None) == 0.25


def test_falls_back_to_global_default() -> None:
    assert _mutation_chance(None, None) == DEFAULT_MUTATION_CHANCE


def _run_cli(*args: str) -> str:
    """Startet die CLI als eigenen Prozess mit Pipe, ohne UTF-8-Modus von aussen."""
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    result = subprocess.run(
        [sys.executable, "-m", "codename_generator.cli", *args],
        capture_output=True,
        env=env,
        check=True,
    )
    return result.stdout.decode("utf-8")


def test_pipe_output_is_utf8() -> None:
    """Unter Windows schrieb die Pipe cp1252 - "Stürzender" kam kaputt an."""
    out = _run_cli("-t", "tierwelt", "-n", "40", "--seed", "3")
    assert any(ch in out for ch in "äöüß"), out


def test_word_with_partner_theme_in_front() -> None:
    out = _run_cli("-w", "Sitemap", "-t", "constellations", "--position", "front", "-n", "5")
    # Zeile: " 1. * Sitemap Alkaid   sitemap-alkaid" - Nummer und Mutationsstern ab.
    names = [line.split(".", 1)[1].lstrip(" *").split()[0] for line in out.splitlines() if line]
    assert names == ["Sitemap"] * 5, out
