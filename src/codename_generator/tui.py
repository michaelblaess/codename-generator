from __future__ import annotations

from typing import ClassVar

import pyperclip
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, ListItem, ListView, Static

from codename_generator.generator import Generator, Suggestion

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


class CodenameApp(App[None]):
    CSS = """
    Screen {
        layers: base overlay;
    }
    #main {
        layout: horizontal;
        height: 1fr;
    }
    #themes {
        width: 28;
        border-right: tall $panel;
    }
    #right {
        width: 1fr;
        padding: 0 1;
    }
    #info {
        height: 3;
        color: $text-muted;
        padding: 0 1;
    }
    DataTable {
        height: 1fr;
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
            with Vertical(id="themes"):
                yield Static("[b]Themes[/b]")
                yield ListView(
                    *[
                        ListItem(
                            Static(f"{self.generator.themes[s].name}"),
                            id=f"theme-{s}",
                        )
                        for s in self.theme_slugs
                    ],
                    id="theme-list",
                )
            with Vertical(id="right"):
                yield Static(id="info")
                table: DataTable[str] = DataTable(
                    cursor_type="row",
                    zebra_stripes=True,
                    id="suggestions",
                )
                table.add_columns("#", "Name", "Slug", "Pattern", "*")
                yield table
        yield Footer()

    def on_mount(self) -> None:
        self.theme = _TEXTUAL_THEMES[self.theme_idx]
        self.title = "codename-generator"
        self.sub_title = self.theme_slug
        list_view = self.query_one("#theme-list", ListView)
        list_view.index = 0
        self._regenerate()

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
                self._regenerate()

    def action_regenerate(self) -> None:
        self._regenerate()

    def action_copy_slug(self) -> None:
        s = self._selected_suggestion()
        if s is None:
            return
        try:
            pyperclip.copy(s.slug)
            self.notify(f"Copied slug: {s.slug}", timeout=2)
        except pyperclip.PyperclipException as exc:
            self.notify(f"Clipboard error: {exc}", severity="error")

    def action_copy_name(self) -> None:
        s = self._selected_suggestion()
        if s is None:
            return
        try:
            pyperclip.copy(s.name)
            self.notify(f"Copied name: {s.name}", timeout=2)
        except pyperclip.PyperclipException as exc:
            self.notify(f"Clipboard error: {exc}", severity="error")

    def action_cycle_mutation(self) -> None:
        self.mutation_idx = (self.mutation_idx + 1) % len(self.MUTATION_LEVELS)
        self._regenerate()

    def action_cycle_theme(self) -> None:
        self.theme_idx = (self.theme_idx + 1) % len(_TEXTUAL_THEMES)
        self.theme = _TEXTUAL_THEMES[self.theme_idx]
        self._update_info()

    def action_toggle_favorite(self) -> None:
        s = self._selected_suggestion()
        if s is None:
            return
        existing = next((f for f in self.favorites if f.slug == s.slug), None)
        if existing is not None:
            self.favorites.remove(existing)
            self.notify(f"Removed favorite: {s.name}")
        else:
            self.favorites.append(s)
            self.notify(f"Added favorite: {s.name}")
        self._update_info()

    def action_open_favorites(self) -> None:
        self.push_screen(FavoritesScreen(self.favorites))


def run_tui() -> None:
    CodenameApp().run()
