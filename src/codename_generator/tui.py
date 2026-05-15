from __future__ import annotations

from datetime import datetime
from typing import ClassVar

import pyperclip
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, ListItem, ListView, RichLog, Static
from textual_slider import Slider
from textual_themes import register_all
from textual_widgets import HorizontalSplitter, VerticalSplitter

from codename_generator import __author__, __version__, __year__
from codename_generator.generator import RANDOM_THEME_SLUG, Generator, Pattern, Suggestion
from codename_generator.settings import JsonSettingsStore

_DICKINSON_QUOTE = "That it will never come again is what makes life so sweet."


class FavoritesScreen(ModalScreen[None]):
    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape,q,Q,v,V", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    FavoritesScreen {
        align: center middle;
    }
    #fav-box {
        width: 80%;
        height: 80%;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    """

    def __init__(self, favorites: list[Suggestion]) -> None:
        super().__init__()
        self.favorites = favorites

    def compose(self) -> ComposeResult:
        with Vertical(id="fav-box"):
            yield Static("[b]Favorites[/b]   (Esc to close)")
            table: DataTable[str] = DataTable(zebra_stripes=True)
            table.add_columns("Name", "Slug", "Pattern", "Mutated")
            for fav in self.favorites:
                table.add_row(fav.name, fav.slug, fav.pattern.value, "yes" if fav.mutated else "")
            if not self.favorites:
                table.add_row("(no favorites yet)", "", "", "")
            yield table


class AboutScreen(ModalScreen[None]):
    """Modal-Dialog mit Informationen ueber die Anwendung."""

    DEFAULT_CSS = """
    AboutScreen {
        align: center middle;
    }

    AboutScreen > VerticalScroll {
        width: auto;
        height: auto;
        min-width: 56;
        max-width: 90;
        max-height: 90%;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    AboutScreen #about-title {
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: $accent;
        color: auto;
        margin-bottom: 1;
    }

    AboutScreen #about-content {
        height: auto;
        padding: 1 2;
    }

    AboutScreen #about-footer {
        height: 1;
        content-align: center middle;
        color: $text-muted;
        margin-top: 1;
    }
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape", "close", "ESC"),
        Binding("a,A,q,Q,enter,space", "close", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static("codename-generator", id="about-title")
            yield Static(self._build_content(), id="about-content")
            yield Static("press [b]a[/b] / [b]Esc[/b] to close", id="about-footer", markup=True)

    def _build_content(self) -> Text:
        text = Text()
        text.append(f"v{__version__}", style="bold")
        text.append(" - ", style="dim")
        text.append(__author__, style="bold")
        text.append(" - ", style="dim")
        text.append(__year__, style="bold")
        text.append("\n\n")

        text.append("Project codename generator with curated themes\n")
        text.append("and phonetic mutations.\n\n")

        text.append("Themes  ", style="dim")
        text.append(
            "Greek/Egyptian/Norse Gods · Constellations · "
            "Racehorses · Flowers · Gemstones · Wines · Whisky · "
            "Mountains · Mushrooms · Ships · Landmarks · Random\n\n"
        )

        text.append("Keys    ", style="dim")
        text.append("r ", style="bold")
        text.append("regenerate  ")
        text.append("c ", style="bold")
        text.append("copy slug  ")
        text.append("n ", style="bold")
        text.append("copy name\n        ")
        text.append("m ", style="bold")
        text.append("mutation  ")
        text.append("t ", style="bold")
        text.append("cycle theme  ")
        text.append("f ", style="bold")
        text.append("favorite\n        ")
        text.append("v ", style="bold")
        text.append("view favs  ")
        text.append("a ", style="bold")
        text.append("about  ")
        text.append("q ", style="bold")
        text.append("quit\n\n")

        text.append("-" * 48 + "\n\n", style="dim")

        text.append(
            f'"{_DICKINSON_QUOTE}"\n\n',
            style="italic",
        )
        text.append(" " * 22)
        text.append("- Emily Dickinson", style="bold")

        return text

    def action_close(self) -> None:
        self.dismiss(None)


class CodenameApp(App[None]):
    CSS = """
    #main {
        layout: horizontal;
        height: 1fr;
    }
    #themes-pane {
        width: 28;
    }
    #themes-pane > Static {
        padding: 0 1;
    }
    #right-pane {
        width: 1fr;
        padding: 0 1;
    }
    #controls {
        height: 3;
        padding: 0 1;
        align: left middle;
    }
    #info {
        width: 1fr;
        color: $text-muted;
        content-align: left middle;
    }
    #mutation-slider {
        width: 24;
    }
    #mutation-label {
        width: 22;
        color: $text-muted;
        content-align: right middle;
    }
    #suggestions {
        height: 1fr;
    }
    #log {
        height: 6;
        background: $boost;
        padding: 0 1;
    }
    ListView > ListItem.--highlight {
        background: $accent 40%;
    }
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("r,R", "regenerate", "Regenerate", key_display="r"),
        Binding("c,C", "copy_slug", "Copy slug", key_display="c"),
        Binding("n,N", "copy_name", "Copy name", key_display="n"),
        Binding("m,M", "bump_mutation", "Mutation +25%", key_display="m"),
        Binding("t,T", "cycle_theme", "Theme", key_display="t"),
        Binding("f,F", "toggle_favorite", "Fav", key_display="f"),
        Binding("v,V", "open_favorites", "View favs", key_display="v"),
        Binding("a,A", "about", "About", key_display="a"),
        Binding("q,Q", "quit", "Quit", key_display="q"),
    ]

    MUTATION_DEFAULT: ClassVar[int] = 35
    MUTATION_BUMP: ClassVar[int] = 25
    DEFAULT_THEME: ClassVar[str] = "textual-dark"

    def __init__(self) -> None:
        super().__init__()
        self._settings_store = JsonSettingsStore()
        register_all(self)  # type: ignore[arg-type]

        self.generator = Generator.load()
        self.theme_slugs = list(self.generator.themes.keys())
        self.theme_slug = self.theme_slugs[0] if self.theme_slugs else ""
        self.suggestions: list[Suggestion] = []

        settings = self._settings_store.load()
        self.mutation_percent = self._coerce_mutation(settings.get("mutation_percent"))
        self.favorites = self._deserialize_favorites(settings.get("favorites"))
        self._startup_theme = str(settings.get("theme", "")) or self.DEFAULT_THEME

    @staticmethod
    def _coerce_mutation(raw: object) -> int:
        if not isinstance(raw, (int, float, str)):
            return CodenameApp.MUTATION_DEFAULT
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return CodenameApp.MUTATION_DEFAULT
        return max(0, min(100, value - (value % 5)))

    @staticmethod
    def _deserialize_favorites(raw: object) -> list[Suggestion]:
        if not isinstance(raw, list):
            return []
        result: list[Suggestion] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                result.append(
                    Suggestion(
                        name=str(item["name"]),
                        slug=str(item["slug"]),
                        pattern=Pattern(str(item["pattern"])),
                        mutated=bool(item["mutated"]),
                        source_words=tuple(str(w) for w in item["source_words"]),
                    )
                )
            except (KeyError, ValueError, TypeError):
                continue
        return result

    def _serialize_favorites(self) -> list[dict[str, object]]:
        return [
            {
                "name": f.name,
                "slug": f.slug,
                "pattern": f.pattern.value,
                "mutated": f.mutated,
                "source_words": list(f.source_words),
            }
            for f in self.favorites
        ]

    def _save_settings(self) -> None:
        self._settings_store.save(
            {
                "theme": self.theme,
                "mutation_percent": self.mutation_percent,
                "favorites": self._serialize_favorites(),
            }
        )

    def watch_theme(self, theme_name: str) -> None:
        """Persistiert jede Theme-Aenderung (auch via Ctrl+P Theme-Picker)."""
        if not hasattr(self, "_settings_store"):
            return
        if self._settings_store.load().get("theme") == theme_name:
            return
        self._save_settings()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="main"):
            with Vertical(id="themes-pane"):
                yield Static("[b]Themes[/b]")
                yield ListView(
                    *[
                        ListItem(
                            Static(self.generator.themes[s].name),
                            id=f"theme-{s}",
                        )
                        for s in self.theme_slugs
                    ],
                    id="theme-list",
                )
            yield VerticalSplitter(target_id="themes-pane", min_size=16, max_size=60)
            with Vertical(id="right-pane"):
                with Horizontal(id="controls"):
                    yield Static(id="info")
                    yield Slider(
                        min=0,
                        max=100,
                        step=5,
                        value=self.mutation_percent,
                        id="mutation-slider",
                    )
                    yield Static(id="mutation-label")
                table: DataTable[str] = DataTable(
                    cursor_type="row",
                    zebra_stripes=True,
                    id="suggestions",
                )
                table.add_columns("#", "Name", "Slug", "Pattern", "*")
                yield table
                yield HorizontalSplitter(target_id="suggestions", min_size=6)
                yield RichLog(id="log", wrap=False, highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        if self._startup_theme in self.available_themes:
            self.theme = self._startup_theme
        self.title = "codename-generator"
        self.sub_title = self.theme_slug
        list_view = self.query_one("#theme-list", ListView)
        list_view.index = 0
        self._log_event(f"started - theme [b]{self.theme_slug}[/b]")
        self._regenerate()

    def _log_event(self, message: str) -> None:
        try:
            log = self.query_one("#log", RichLog)
        except Exception:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        log.write(f"[dim]{timestamp}[/dim]  {message}")

    def _update_info(self) -> None:
        info = self.query_one("#info", Static)
        info.update(
            f"[b]{self.generator.themes[self.theme_slug].name}[/b]   "
            f"theme: [b]{self.theme}[/b]   "
            f"favorites: [b]{len(self.favorites)}[/b]"
        )
        label = self.query_one("#mutation-label", Static)
        label.update(f"mutation: [b]{self.mutation_percent}%[/b]")

    def _regenerate(self) -> None:
        if not self.theme_slug:
            return
        mutation = self.mutation_percent / 100.0
        self.suggestions = self.generator.suggest(
            theme_slug=self.theme_slug,
            count=30,
            mutation_chance=mutation,
        )
        table = self.query_one("#suggestions", DataTable)
        table.clear()
        for i, s in enumerate(self.suggestions, 1):
            table.add_row(
                str(i),
                s.name,
                s.slug,
                s.pattern.value,
                "*" if s.mutated else "",
            )
        self._update_info()

    def _selected_suggestion(self) -> Suggestion | None:
        table = self.query_one("#suggestions", DataTable)
        if table.row_count == 0:
            return None
        row = table.cursor_row
        if 0 <= row < len(self.suggestions):
            return self.suggestions[row]
        return None

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self._switch_theme(event.item.id or "")

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None:
            return
        self._switch_theme(event.item.id or "")

    def _switch_theme(self, item_id: str) -> None:
        if not item_id.startswith("theme-"):
            return
        slug = item_id[len("theme-") :]
        if slug in self.generator.themes and slug != self.theme_slug:
            self.theme_slug = slug
            self.sub_title = slug
            self._log_event(f"theme -> [b]{slug}[/b]")
            self._regenerate()

    def action_regenerate(self) -> None:
        self._log_event("regenerated")
        self._regenerate()

    def action_copy_slug(self) -> None:
        s = self._selected_suggestion()
        if s is None:
            return
        try:
            pyperclip.copy(s.slug)
            self.notify(f"Copied slug: {s.slug}", timeout=2)
            self._log_event(f"copied slug [b]{s.slug}[/b]")
        except pyperclip.PyperclipException as exc:
            self.notify(f"Clipboard error: {exc}", severity="error")
            self._log_event(f"[red]clipboard error: {exc}[/red]")

    def action_copy_name(self) -> None:
        s = self._selected_suggestion()
        if s is None:
            return
        try:
            pyperclip.copy(s.name)
            self.notify(f"Copied name: {s.name}", timeout=2)
            self._log_event(f"copied name [b]{s.name}[/b]")
        except pyperclip.PyperclipException as exc:
            self.notify(f"Clipboard error: {exc}", severity="error")
            self._log_event(f"[red]clipboard error: {exc}[/red]")

    def action_bump_mutation(self) -> None:
        new_value = (self.mutation_percent + self.MUTATION_BUMP) % 105
        new_value = min(100, new_value - (new_value % 5))
        self.mutation_percent = new_value
        slider = self.query_one("#mutation-slider", Slider)
        slider.value = new_value
        self._log_event(f"mutation -> [b]{new_value}%[/b]")
        self._save_settings()
        self._regenerate()

    def on_slider_changed(self, event: Slider.Changed) -> None:
        if event.slider.id != "mutation-slider":
            return
        new_value = int(event.value)
        if new_value == self.mutation_percent:
            return
        self.mutation_percent = new_value
        self._log_event(f"mutation -> [b]{new_value}%[/b]")
        self._save_settings()
        self._regenerate()

    def action_cycle_theme(self) -> None:
        themes = sorted(self.available_themes)
        if not themes:
            return
        try:
            idx = themes.index(self.theme)
        except ValueError:
            idx = -1
        self.theme = themes[(idx + 1) % len(themes)]
        self._log_event(f"theme -> [b]{self.theme}[/b]")
        self._update_info()

    def action_toggle_favorite(self) -> None:
        s = self._selected_suggestion()
        if s is None:
            return
        existing = next((f for f in self.favorites if f.slug == s.slug), None)
        if existing is not None:
            self.favorites.remove(existing)
            self.notify(f"Removed favorite: {s.name}")
            self._log_event(f"unfav [b]{s.name}[/b]")
        else:
            self.favorites.append(s)
            self.notify(f"Added favorite: {s.name}")
            self._log_event(f"fav [b]{s.name}[/b]")
        self._save_settings()
        self._update_info()

    def action_open_favorites(self) -> None:
        self.push_screen(FavoritesScreen(self.favorites))

    def action_about(self) -> None:
        self.push_screen(AboutScreen())


def run_tui() -> None:
    CodenameApp().run()


__all__ = ["RANDOM_THEME_SLUG", "CodenameApp", "run_tui"]
