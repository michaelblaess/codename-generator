from __future__ import annotations

import json
from pathlib import Path

import codename_generator.settings as settings_mod
from codename_generator.settings import JsonSettingsStore


def test_load_missing_file_returns_empty(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings_mod, "_SETTINGS_FILE", tmp_path / "missing.json")
    assert JsonSettingsStore().load() == {}


def test_save_then_load_roundtrip(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(settings_mod, "_SETTINGS_DIR", tmp_path)
    monkeypatch.setattr(settings_mod, "_SETTINGS_FILE", tmp_path / "settings.json")
    store = JsonSettingsStore()
    store.save({"theme": "nord", "mutation_percent": 60})
    assert store.load() == {"theme": "nord", "mutation_percent": 60}


def test_load_corrupt_file_returns_empty(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    corrupt = tmp_path / "settings.json"
    corrupt.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(settings_mod, "_SETTINGS_FILE", corrupt)
    assert JsonSettingsStore().load() == {}


def test_load_non_dict_returns_empty(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    arr = tmp_path / "settings.json"
    arr.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    monkeypatch.setattr(settings_mod, "_SETTINGS_FILE", arr)
    assert JsonSettingsStore().load() == {}
