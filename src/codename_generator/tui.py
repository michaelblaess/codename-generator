from __future__ import annotations

from datetime import datetime
from typing import ClassVar

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
from codename_generator.generator import (
    RANDOM_THEME_SLUG,
    Generator,
    Pattern,
    Recipe,
    Suggestion,
)
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
    #info {
        height: 1;
        color: $text-muted;
        content-align: left middle;
        padding: 0 1;
    }
    #theme-list {
        height: 1fr;
    }
    #settings-pane {
        height: 15;
        padding: 1 2;
        background: $boost;
    }
    #settings-title {
        text-style: bold;
        padding: 0 0 1 0;
    }
    .settings-label {
        color: $text-muted;
        padding: 0;
    }
    .settings-label.locked {
        color: $text-disabled;
    }
    .settings-slider {
        width: 1fr;
        margin-bottom: 1;
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
    WORD_COUNT_DEFAULT: ClassVar[int] = 2
    DEFAULT_THEME: ClassVar[str] = "textual-dark"

    def __init__(self) -> None:
        super().__init__()
        self._settings_store = JsonSettingsStore()
        register_all(self)  # type: ignore[arg-type]

        self.generator = Generator.load()
        self.theme_slugs = list(self.generator.themes.keys())
        self.theme_slug = self.theme_slugs[0] if self.theme_slugs else ""
        self.suggestions: list[Suggestion] = []
        # Recipes pro Theme - bleiben erhalten bis "r" neue erzeugt.
        self._recipes: dict[str, list[Recipe]] = {}

        settings = self._settings_store.load()
        self.mutation_percent = self._coerce_mutation(settings.get("mutation_percent"))
        self.word_count = self._coerce_words(settings.get("word_count"))
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
    def _coerce_words(raw: object) -> int:
        if not isinstance(raw, (int, float, str)):
            return CodenameApp.WORD_COUNT_DEFAULT
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return CodenameApp.WORD_COUNT_DEFAULT
        return max(1, min(3, value))

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
                "word_count": self.word_count,
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

    def _theme_items(self) -> list[ListItem]:
        """Baut die Theme-Listeneintraege - Beschreibung als Hover-Tooltip."""
        items: list[ListItem] = []
        for slug in self.theme_slugs:
            theme = self.generator.themes[slug]
            item = ListItem(Static(theme.name), id=f"theme-{slug}")
            if theme.description:
                item.tooltip = theme.description
            items.append(item)
        return items

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="main"):
            with Vertical(id="themes-pane"):
                yield Static("[b]Themes[/b]")
                yield ListView(*self._theme_items(), id="theme-list")
                yield HorizontalSplitter(target_id="theme-list", min_size=6)
                with Vertical(id="settings-pane"):
                    yield Static("Settings", id="settings-title")
                    yield Static(id="mutation-label", classes="settings-label")
                    yield Slider(
                        min=0,
                        max=100,
                        step=5,
                        value=self.mutation_percent,
                        id="mutation-slider",
                        classes="settings-slider",
                    )
                    yield Static(id="wordcount-label", classes="settings-label")
                    yield Slider(
                        min=1,
                        max=3,
                        step=1,
                        value=self.word_count,
                        id="wordcount-slider",
                        classes="settings-slider",
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
        if self._startup_theme in self.available_themes:
            self.theme = self._startup_theme
        self.title = "codename-generator"
        self.sub_title = self.theme_slug
        list_view = self.query_one("#theme-list", ListView)
        list_view.index = 0
        self._log_event(f"started - theme [b]{self.theme_slug}[/b]")
        self._ensure_recipes()
        self._rerender()

    def _log_event(self, message: str) -> None:
        try:
            log = self.query_one("#log", RichLog)
        except Exception:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        log.write(f"[dim]{timestamp}[/dim]  {message}")

    def _update_info(self) -> None:
        theme = self.generator.themes[self.theme_slug]
        info = self.query_one("#info", Static)
        info.update(
            f"[b]{theme.name}[/b]  [dim]{theme.description}[/dim]   "
            f"favorites: [b]{len(self.favorites)}[/b]"
        )

        # Themes mit eigenen Patterns / mutate=false machen die Slider wirkungslos.
        mutation_locked = not theme.mutate
        words_locked = bool(theme.patterns)

        mut_label = self.query_one("#mutation-label", Static)
        wc_label = self.query_one("#wordcount-label", Static)
        self.query_one("#mutation-slider", Slider).disabled = mutation_locked
        self.query_one("#wordcount-slider", Slider).disabled = words_locked
        mut_label.set_class(mutation_locked, "locked")
        wc_label.set_class(words_locked, "locked")

        mut_label.update(
            "Mutation: [b]locked by theme[/b]"
            if mutation_locked
            else f"Mutation: [b]{self.mutation_percent}%[/b]"
        )
        wc_label.update(
            "Words: [b]locked by theme[/b]"
            if words_locked
            else f"Words: [b]{self.word_count}[/b]"
        )

    def _ensure_recipes(self) -> None:
        """Erzeugt Recipes fuer das aktuelle Theme, falls noch keine im Cache."""
        if self.theme_slug and self.theme_slug not in self._recipes:
            self._recipes[self.theme_slug] = self.generator.generate_recipes(
                self.theme_slug, count=30
            )

    def _fresh_recipes(self) -> None:
        """Verwirft die Recipes des aktuellen Themes und erzeugt neue."""
        if self.theme_slug:
            self._recipes[self.theme_slug] = self.generator.generate_recipes(
                self.theme_slug, count=30
            )

    def _rerender(self) -> None:
        """Rendert die vorhandenen Recipes mit aktueller Mutation/Wortzahl neu.

        Erzeugt KEINE neuen Recipes - die Grundzutaten bleiben stabil, nur die
        Darstellung (Mutation, Wortzahl) aendert sich.
        """
        if not self.theme_slug:
            return
        theme = self.generator.themes[self.theme_slug]
        mutation = self.mutation_percent / 100.0
        recipes = self._recipes.get(self.theme_slug, [])
        self.suggestions = [
            self.generator.render(r, theme, self.word_count, mutation) for r in recipes
        ]
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
            self._apply_theme_default_mutation()
            self._log_event(f"theme -> [b]{slug}[/b]")
            # Vorhandene Recipes des Themes bleiben erhalten (Cache).
            self._ensure_recipes()
            self._rerender()

    def _apply_theme_default_mutation(self) -> None:
        """Setzt die Mutation auf den Theme-Default beim Wechsel (falls deklariert)."""
        theme = self.generator.themes[self.theme_slug]
        if theme.default_mutation is None:
            return
        value = max(0, min(100, theme.default_mutation - (theme.default_mutation % 5)))
        if value == self.mutation_percent:
            return
        self.mutation_percent = value
        self.query_one("#mutation-slider", Slider).value = value
        self._save_settings()

    def action_regenerate(self) -> None:
        self._fresh_recipes()
        self._log_event("regenerated")
        self._rerender()

    def action_copy_slug(self) -> None:
        s = self._selected_suggestion()
        if s is None:
            return
        # copy_to_clipboard reicht den Befehl ans Terminal bzw. den Browser
        # durch - funktioniert lokal, ueber SSH und web-gehostet (textual-web).
        self.copy_to_clipboard(s.slug)
        self.notify(f"Copied slug: {s.slug}", timeout=2)
        self._log_event(f"copied slug [b]{s.slug}[/b]")

    def action_copy_name(self) -> None:
        s = self._selected_suggestion()
        if s is None:
            return
        self.copy_to_clipboard(s.name)
        self.notify(f"Copied name: {s.name}", timeout=2)
        self._log_event(f"copied name [b]{s.name}[/b]")

    def action_bump_mutation(self) -> None:
        if not self.generator.themes[self.theme_slug].mutate:
            self.notify("Mutation is locked for this theme", severity="warning")
            return
        new_value = (self.mutation_percent + self.MUTATION_BUMP) % 105
        new_value = min(100, new_value - (new_value % 5))
        self.mutation_percent = new_value
        slider = self.query_one("#mutation-slider", Slider)
        slider.value = new_value
        self._log_event(f"mutation -> [b]{new_value}%[/b]")
        self._save_settings()
        self._rerender()

    def on_slider_changed(self, event: Slider.Changed) -> None:
        new_value = int(event.value)
        if event.slider.id == "mutation-slider":
            if new_value == self.mutation_percent:
                return
            self.mutation_percent = new_value
            self._log_event(f"mutation -> [b]{new_value}%[/b]")
        elif event.slider.id == "wordcount-slider":
            if new_value == self.word_count:
                return
            self.word_count = new_value
            self._log_event(f"word count -> [b]{new_value}[/b]")
        else:
            return
        self._save_settings()
        self._rerender()

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
