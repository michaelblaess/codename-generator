"""Uebersicht der aktuell geltenden Tastenbelegung (Taste ?).

Die Seite liest nichts eigenes - sie stellt dar, was `keymap.resolve()` aus
Stil, Vim-Schalter und eigenen Belegungen gemacht hat. Damit stimmt sie
zwangslaeufig mit dem ueberein, was die Anwendung tatsaechlich gebunden hat,
statt eine gepflegte Liste danebenzustellen, die irgendwann abweicht (wie die
fest eingetippte Tastenliste im frueheren About-Dialog). Vorbild:
jira-timesheet, `screens/keymap_screen.py`.
"""

from __future__ import annotations

from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static
from textual_widgets.keymap import KeymapStyle, ResolvedKeymap

from codename_generator.keymap import LABELS, key_display

_STYLE_TEXT = {
    KeymapStyle.CLASSIC: "Classic (letters only)",
    KeymapStyle.FUNCTION_KEYS: "With function keys",
}


class KeymapScreen(ModalScreen[None]):
    """Zeigt Taste und Aktion der aktiven Belegung."""

    DEFAULT_CSS = """
    KeymapScreen {
        align: center middle;
    }

    KeymapScreen > Vertical {
        width: 64;
        max-width: 90%;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    KeymapScreen #keymap-title {
        text-align: center;
        text-style: bold;
        color: $primary;
    }

    KeymapScreen #keymap-mode {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }

    KeymapScreen VerticalScroll {
        height: auto;
        max-height: 24;
    }

    KeymapScreen DataTable {
        height: auto;
    }

    KeymapScreen #keymap-close {
        margin-top: 1;
        width: 100%;
    }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "dismiss", "Esc"),
        Binding("q,Q,question_mark", "dismiss", "Close", show=False),
    ]

    def __init__(self, resolved: ResolvedKeymap, style: KeymapStyle, vim: bool) -> None:
        super().__init__()
        self._resolved = resolved
        self._style = style
        self._vim = vim

    def compose(self) -> ComposeResult:
        """Baut Titel, Modus-Zeile, Tabelle und den Schliessen-Knopf."""
        vim_text = "vim navigation on" if self._vim else "vim navigation off"
        with Vertical():
            yield Static("Keys", id="keymap-title")
            yield Static(f"{_STYLE_TEXT[self._style]} - {vim_text}", id="keymap-mode")
            with VerticalScroll():
                yield DataTable(id="keymap-table", cursor_type="row", zebra_stripes=True)
            yield Button("Close (Esc)", variant="primary", id="keymap-close")

    def on_mount(self) -> None:
        """Fuellt die Tabelle aus der aufgeloesten Belegung."""
        table: DataTable[str] = self.query_one("#keymap-table", DataTable)
        table.add_column("Key", width=20)
        table.add_column("Action")
        for action, binding in self._resolved.bindings.items():
            keys = " / ".join(key_display(key) for key in binding.keys if not _is_shifted(key))
            label = LABELS.get(action, action)
            if not binding.show:
                label = f"{label}  (hidden in footer)"
            table.add_row(keys, label)
        self.set_focus(self.query_one("#keymap-close", Button))

    @on(Button.Pressed, "#keymap-close")
    def _on_close(self) -> None:
        """Schliesst die Uebersicht."""
        self.dismiss(None)


def _is_shifted(key: str) -> bool:
    """Prueft, ob eine Taste nur die Grossschreibung einer anderen ist.

    Die Belegung fuehrt Buchstaben doppelt (``q`` und ``Q``), damit sie
    unabhaengig von der Umschalttaste wirken - in der Uebersicht genuegt die
    Kleinschreibung.

    Args:
        key: Der Tastenname.

    Returns:
        True, wenn es ein einzelner Grossbuchstabe ist.
    """
    return len(key) == 1 and key.isupper()
