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
from textual_widgets import HorizontalSplitter, VerticalSplitter

from codename_generator import __author__, __version__, __year__
from codename_generator.generator import RANDOM_THEME_SLUG, Generator, Suggestion

_TEXTUAL_THEMES = (
    "textual-dark",
    "textual-light",
    "nord",
    "gruvbox",
    "catppuccin-mocha",
    "catppuccin-latte",
    "dracula",
    "tokyo-night",
    "monokai",
    "flexoki",
    "solarized-light",
)

_DICKINSON_QUOTE = "That it will never come again is what makes life so sweet."


class FavoritesScreen(ModalScreen[None]):
    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("escape,q,f", "dismiss", "Close"),
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
        color: $text;
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
        Binding("a,q,enter,space", "close", "Close"),
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
        text.append("textual theme  ")
        text.append("f ", style="bold")
        text.append("favorite\n        ")
        text.append("F ", style="bold")
        text.append("show favs  ")
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
    #info {
        height: 3;
        color: $text-muted;
        padding: 0 1;
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
        Binding("r", "regenerate", "Regenerate"),
        Binding("c", "copy_slug", "Copy slug"),
        Binding("n", "copy_name", "Copy name"),
        Binding("m", "cycle_mutation", "Mutation"),
        Binding("t", "cycle_theme", "Theme"),
        Binding("f", "toggle_favorite", "Fav"),
        Binding("F", "open_favorites", "Show favs"),
        Binding("a", "about", "About"),
        Binding("q", "quit", "Quit"),
    ]

    MUTATION_LEVELS: ClassVar[tuple[float, ...]] = (0.0, 0.2, 0.35, 0.6, 1.0)

    def __init__(self) -> None:
        super().__init__()
        self.generator = Generator.load()
        self.theme_slugs = list(self.generator.themes.keys())
        self.theme_slug = self.theme_slugs[0] if self.theme_slugs else ""
        self.mutation_idx = 2
        self.theme_idx = 0
        self.suggestions: list[Suggestion] = []
        self.favorites: list[Suggestion] = []

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
                yield Static(id="info")
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
        self.theme = _TEXTUAL_THEMES[self.theme_idx]
        self.title = "codename-generator"
        self.sub_title = self.theme_slug
        list_view = self.query_one("#theme-list", ListView)
        list_view.index = 0
        self._log_event(f"started - theme [b]{self.theme_slug}[/b]")
        self._regenerate()

    def _log_event(self, message: str) -> None:
        log = self.query_one("#log", RichLog)
        timestamp = datetime.now().strftime("%H:%M:%S")
        log.write(f"[dim]{timestamp}[/dim]  {message}")

    def _update_info(self) -> None:
        mutation = self.MUTATION_LEVELS[self.mutation_idx]
        info = self.query_one("#info", Static)
        info.update(
            f"[b]{self.generator.themes[self.theme_slug].name}[/b]   "
            f"mutation chance: [b]{mutation:.0%}[/b]   "
            f"theme: [b]{self.theme}[/b]   "
            f"favorites: [b]{len(self.favorites)}[/b]"
        )

    def _regenerate(self) -> None:
        if not self.theme_slug:
            return
        mutation = self.MUTATION_LEVELS[self.mutation_idx]
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
        item_id = event.item.id or ""
        if item_id.startswith("theme-"):
            slug = item_id[len("theme-") :]
            if slug in self.generator.themes:
                self.theme_slug = slug
                self.sub_title = slug
                self._log_event(f"theme -> [b]{slug}[/b]")
                self._regenerate()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None:
            return
        item_id = event.item.id or ""
        if item_id.startswith("theme-"):
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

    def action_cycle_mutation(self) -> None:
        self.mutation_idx = (self.mutation_idx + 1) % len(self.MUTATION_LEVELS)
        mutation = self.MUTATION_LEVELS[self.mutation_idx]
        self._log_event(f"mutation chance -> [b]{mutation:.0%}[/b]")
        self._regenerate()

    def action_cycle_theme(self) -> None:
        self.theme_idx = (self.theme_idx + 1) % len(_TEXTUAL_THEMES)
        self.theme = _TEXTUAL_THEMES[self.theme_idx]
        self._log_event(f"textual theme -> [b]{self.theme}[/b]")
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
        self._update_info()

    def action_open_favorites(self) -> None:
        self.push_screen(FavoritesScreen(self.favorites))

    def action_about(self) -> None:
        self.push_screen(AboutScreen())


def run_tui() -> None:
    CodenameApp().run()


__all__ = ["RANDOM_THEME_SLUG", "CodenameApp", "run_tui"]
