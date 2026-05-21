from __future__ import annotations

import re
import sys
from datetime import datetime
from typing import ClassVar

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Click
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    ListItem,
    ListView,
    RichLog,
    Select,
    Static,
)
from textual_slider import Slider
from textual_themes import register_all
from textual_widgets import (
    ContextMenuItem,
    ContextMenuScreen,
    HorizontalSplitter,
    TextInputScreen,
    VerticalSplitter,
)

from codename_generator import __author__, __version__, __year__
from codename_generator.effects import EFFECT_NONE, EFFECTS, is_valid_effect, play_effect
from codename_generator.generator import (
    CUSTOM_SEED_SLUG,
    RANDOM_THEME_SLUG,
    Generator,
    Pattern,
    Recipe,
    Suggestion,
)
from codename_generator.settings import JsonSettingsStore

_DICKINSON_QUOTE = "That it will never come again is what makes life so sweet."

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify_name(text: str) -> str:
    """Erzeugt einen Slug aus einem freien Text (kleinbuchstaben, Bindestriche)."""
    return _SLUG_RE.sub("-", text.lower()).strip("-")


class SuggestionsTable(DataTable[str]):
    """Vorschlags-Tabelle, die bei Rechtsklick eine RightClicked-Message sendet.

    Textuals DataTable stoppt das Click-Event bei jedem Treffer auf eine Zelle
    (`event.stop()`), sodass ein App-weiter `on_click`-Handler nie ausgeloest
    wird. Darum faengt diese Unterklasse den Rechtsklick selbst ab, setzt den
    Cursor auf die getroffene Zeile und meldet sie per Message an die App.
    """

    class RightClicked(Message):
        """Meldet einen Rechtsklick auf eine Tabellenzeile an die App."""

        def __init__(self, row: int, screen_x: int, screen_y: int) -> None:
            super().__init__()
            self.row = row
            self.screen_x = screen_x
            self.screen_y = screen_y

    async def _on_click(self, event: Click) -> None:
        # button 3 = Rechtsklick (SGR-Maus-Encoding).
        if event.button == 3:
            row = event.style.meta.get("row")
            if isinstance(row, int) and row >= 0:
                self.move_cursor(row=row)
                self.post_message(
                    self.RightClicked(row, event.screen_x, event.screen_y)
                )
            event.stop()
            return
        await super()._on_click(event)


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
            "Animals · Racehorses · Flowers · Gemstones · Wines · Whisky · "
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
        text.append("i ", style="bold")
        text.append("idea seed  ")
        text.append("+ ", style="bold")
        text.append("add idea\n        ")
        text.append("a ", style="bold")
        text.append("about  ")
        text.append("q ", style="bold")
        text.append("quit\n\n")

        text.append("Mouse   ", style="dim")
        text.append("right-click a suggestion for a context menu\n\n")

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
    #fav-theme Static {
        color: $warning;
        text-style: bold;
    }
    #seed-theme Static {
        color: $warning;
        text-style: bold;
    }
    #settings-pane {
        height: auto;
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
    #effect-select {
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
        Binding("i,I", "edit_seed", "Idea seed", key_display="i"),
        Binding("plus", "add_custom_favorite", "Add idea", key_display="+"),
        Binding("a,A", "about", "About", key_display="a"),
        Binding("q,Q", "quit", "Quit", key_display="q"),
    ]

    MUTATION_DEFAULT: ClassVar[int] = 35
    MUTATION_BUMP: ClassVar[int] = 25
    WORD_COUNT_DEFAULT: ClassVar[int] = 2
    SUGGESTION_COUNT_DEFAULT: ClassVar[int] = 30
    DEFAULT_THEME: ClassVar[str] = "textual-dark"
    # ListItem-ID des virtuellen "Favorites"-Eintrags in der Theme-Liste.
    FAVORITES_ITEM_ID: ClassVar[str] = "fav-theme"
    # ListItem-ID des virtuellen "Custom Seed"-Eintrags in der Theme-Liste.
    CUSTOM_SEED_ITEM_ID: ClassVar[str] = "seed-theme"

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
        # Favoriten-Ansicht: rechts die Favoriten statt generierter Vorschlaege.
        self._favorites_mode = False
        # Custom-Seed-Ansicht: rechts Varianten eines vom User eingegebenen Worts.
        self._seed_mode = False

        settings = self._settings_store.load()
        self.mutation_percent = self._coerce_mutation(settings.get("mutation_percent"))
        self.word_count = self._coerce_words(settings.get("word_count"))
        self.suggestion_count = self._coerce_count(settings.get("suggestion_count"))
        self.favorites = self._deserialize_favorites(settings.get("favorites"))
        self._custom_seed = str(settings.get("custom_seed", "")).strip()
        self._effect_name = self._coerce_effect(settings.get("effect"))
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
    def _coerce_count(raw: object) -> int:
        """Normalisiert die Vorschlagsanzahl auf einen 10er-Schritt von 10..40."""
        if not isinstance(raw, (int, float, str)):
            return CodenameApp.SUGGESTION_COUNT_DEFAULT
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return CodenameApp.SUGGESTION_COUNT_DEFAULT
        return max(10, min(40, value - (value % 10)))

    @staticmethod
    def _coerce_effect(raw: object) -> str:
        """Normalisiert den Effekt-Key auf einen bekannten Slug oder 'none'."""
        if not isinstance(raw, str):
            return EFFECT_NONE
        return raw if is_valid_effect(raw) else EFFECT_NONE

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
                "suggestion_count": self.suggestion_count,
                "favorites": self._serialize_favorites(),
                "custom_seed": self._custom_seed,
                "effect": self._effect_name,
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
        """Baut die Theme-Listeneintraege - Favorites + Custom Seed oben, dann die Themes."""
        fav_item = ListItem(Static("Favorites"), id=self.FAVORITES_ITEM_ID)
        fav_item.tooltip = "Your saved codenames"
        seed_label = f"Custom Seed: {self._custom_seed}" if self._custom_seed else "Custom Seed"
        seed_item = ListItem(Static(seed_label), id=self.CUSTOM_SEED_ITEM_ID)
        seed_item.tooltip = "Combine your own word with adjectives and verbs"
        items: list[ListItem] = [fav_item, seed_item]
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
                    yield Static(id="count-label", classes="settings-label")
                    yield Slider(
                        min=10,
                        max=40,
                        step=10,
                        value=self.suggestion_count,
                        id="count-slider",
                        classes="settings-slider",
                    )
                    yield Static("Effect", id="effect-label", classes="settings-label")
                    yield Select(
                        [(label, key) for key, label in EFFECTS],
                        value=self._effect_name,
                        allow_blank=False,
                        id="effect-select",
                    )
            yield VerticalSplitter(target_id="themes-pane", min_size=16, max_size=60)
            with Vertical(id="right-pane"):
                yield Static(id="info")
                table: SuggestionsTable = SuggestionsTable(
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
        # Indizes 0/1 sind Favorites/Custom Seed - Start auf dem ersten echten Theme.
        list_view.index = 2
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
        if self._favorites_mode:
            self._update_favorites_info()
            return
        if self._seed_mode:
            self._update_seed_info()
            return
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

        # Die Vorschlagsanzahl gilt fuer jedes Theme - nie durch das Theme gesperrt.
        # (count-slider explizit entsperren, falls zuvor die Favoriten-Ansicht aktiv war.)
        count_label = self.query_one("#count-label", Static)
        self.query_one("#count-slider", Slider).disabled = False
        count_label.set_class(False, "locked")
        count_label.update(f"Suggestions: [b]{self.suggestion_count}[/b]")

    def _update_seed_info(self) -> None:
        """Info-Zeile und Slider-Status fuer die Custom-Seed-Ansicht.

        Alle drei Slider gelten (Mutation/Wortzahl/Vorschlagsanzahl) - genauso
        wie bei einem normalen Theme. Theme-spezifische Sperren entfallen.
        """
        self.query_one("#info", Static).update(
            f"[b]Custom Seed[/b]  [dim]your idea \"{self._custom_seed}\" combined with "
            "adjectives and verbs - press [b]i[/b] to change[/dim]"
        )
        mut_label = self.query_one("#mutation-label", Static)
        wc_label = self.query_one("#wordcount-label", Static)
        count_label = self.query_one("#count-label", Static)
        self.query_one("#mutation-slider", Slider).disabled = False
        self.query_one("#wordcount-slider", Slider).disabled = False
        self.query_one("#count-slider", Slider).disabled = False
        mut_label.set_class(False, "locked")
        wc_label.set_class(False, "locked")
        count_label.set_class(False, "locked")
        mut_label.update(f"Mutation: [b]{self.mutation_percent}%[/b]")
        wc_label.update(f"Words: [b]{self.word_count}[/b]")
        count_label.update(f"Suggestions: [b]{self.suggestion_count}[/b]")

    def _update_favorites_info(self) -> None:
        """Info-Zeile und Slider-Sperren fuer die Favoriten-Ansicht.

        In der Favoriten-Ansicht wirkt nur der Mutations-Slider - Wortzahl und
        Vorschlagsanzahl sind ohne Bedeutung und werden gesperrt.
        """
        self.query_one("#info", Static).update(
            "[b]Favorites[/b]  [dim]your saved codenames - only mutation "
            f"applies here[/dim]   count: [b]{len(self.favorites)}[/b]"
        )
        mut_label = self.query_one("#mutation-label", Static)
        wc_label = self.query_one("#wordcount-label", Static)
        count_label = self.query_one("#count-label", Static)
        self.query_one("#mutation-slider", Slider).disabled = False
        self.query_one("#wordcount-slider", Slider).disabled = True
        self.query_one("#count-slider", Slider).disabled = True
        mut_label.set_class(False, "locked")
        wc_label.set_class(True, "locked")
        count_label.set_class(True, "locked")
        mut_label.update(f"Mutation: [b]{self.mutation_percent}%[/b]")
        wc_label.update("Words: [b]locked in favorites[/b]")
        count_label.update("Suggestions: [b]locked in favorites[/b]")

    def _ensure_recipes(self) -> None:
        """Erzeugt Recipes fuer das aktuelle Theme, falls noch keine im Cache."""
        if self.theme_slug and self.theme_slug not in self._recipes:
            self._recipes[self.theme_slug] = self.generator.generate_recipes(
                self.theme_slug, count=self.suggestion_count
            )

    def _ensure_seed_recipes(self) -> None:
        """Erzeugt Recipes fuer den aktuellen Custom-Seed, falls noch keine im Cache."""
        if self._custom_seed and CUSTOM_SEED_SLUG not in self._recipes:
            self._recipes[CUSTOM_SEED_SLUG] = self.generator.generate_seeded_recipes(
                self._custom_seed, count=self.suggestion_count
            )

    def _fresh_recipes(self) -> None:
        """Verwirft die Recipes des aktuellen Themes/Seeds und erzeugt neue."""
        if self._seed_mode and self._custom_seed:
            self._recipes[CUSTOM_SEED_SLUG] = self.generator.generate_seeded_recipes(
                self._custom_seed, count=self.suggestion_count
            )
            return
        if self.theme_slug:
            self._recipes[self.theme_slug] = self.generator.generate_recipes(
                self.theme_slug, count=self.suggestion_count
            )

    def _rerender(self) -> None:
        """Rendert die vorhandenen Recipes mit aktueller Mutation/Wortzahl neu.

        Erzeugt KEINE neuen Recipes - die Grundzutaten bleiben stabil, nur die
        Darstellung (Mutation, Wortzahl) aendert sich.
        """
        if self._favorites_mode:
            self._render_favorites()
            return
        if self._seed_mode:
            self._render_seeded()
            return
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

    def _render_seeded(self) -> None:
        """Rendert die Custom-Seed-Recipes mit aktueller Mutation/Wortzahl."""
        if not self._custom_seed:
            return
        theme = self.generator.seeded_theme(self._custom_seed)
        mutation = self.mutation_percent / 100.0
        recipes = self._recipes.get(CUSTOM_SEED_SLUG, [])
        self.suggestions = [
            self.generator.render(r, theme, self.word_count, mutation) for r in recipes
        ]
        table = self.query_one("#suggestions", DataTable)
        table.clear()
        if not self.suggestions:
            table.add_row("", "(no seed yet - press i)", "", "", "")
        else:
            for i, s in enumerate(self.suggestions, 1):
                table.add_row(
                    str(i),
                    s.name,
                    s.slug,
                    s.pattern.value,
                    "*" if s.mutated else "",
                )
        self._update_info()

    def _render_favorites(self) -> None:
        """Zeigt die gespeicherten Favoriten rechts an - mit aktueller Mutation."""
        mutation = self.mutation_percent / 100.0
        self.suggestions = [
            self.generator.render_favorite(fav, mutation) for fav in self.favorites
        ]
        table = self.query_one("#suggestions", DataTable)
        table.clear()
        if not self.suggestions:
            table.add_row("", "(no favorites yet)", "", "", "")
        else:
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
        # Explizite Auswahl (Klick / Enter) - bei leerem Seed Dialog oeffnen.
        self._switch_theme(event.item.id or "", allow_dialog=True)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        # Reine Cursor-Bewegung (Pfeiltasten, oder gleichzeitig mit Klick) -
        # darf NICHT den Seed-Dialog oeffnen, sonst stapeln sich zwei Dialoge
        # uebereinander, weil ein Klick beide Events feuert.
        if event.item is None:
            return
        self._switch_theme(event.item.id or "", allow_dialog=False)

    def _switch_theme(self, item_id: str, *, allow_dialog: bool = True) -> None:
        # Virtueller "Favorites"-Eintrag - rechts die Favoriten anzeigen.
        if item_id == self.FAVORITES_ITEM_ID:
            if not self._favorites_mode:
                self._favorites_mode = True
                self._seed_mode = False
                self.sub_title = "favorites"
                self._log_event("viewing [b]favorites[/b]")
                self._rerender()
            return
        # Virtueller "Custom Seed"-Eintrag - Eingabe abfragen, dann rendern.
        if item_id == self.CUSTOM_SEED_ITEM_ID:
            self._enter_seed_mode(allow_dialog=allow_dialog)
            return
        if not item_id.startswith("theme-"):
            return
        slug = item_id[len("theme-") :]
        if slug not in self.generator.themes:
            return
        was_special = self._favorites_mode or self._seed_mode
        self._favorites_mode = False
        self._seed_mode = False
        if slug == self.theme_slug:
            # Gleiche Theme - nur noetig, wenn wir aus einer Sonderansicht kommen.
            if was_special:
                self.sub_title = slug
                self._rerender()
            return
        self.theme_slug = slug
        self.sub_title = slug
        self._apply_theme_default_mutation()
        self._log_event(f"theme -> [b]{slug}[/b]")
        # Vorhandene Recipes des Themes bleiben erhalten (Cache).
        self._ensure_recipes()
        self._rerender()

    def _enter_seed_mode(self, *, allow_dialog: bool = True) -> None:
        """Wechselt in den Custom-Seed-Mode - bei leerem Seed der Eingabedialog.

        `allow_dialog=False` schaltet das automatische Oeffnen des Dialogs ab.
        Wird vom Highlight-Handler verwendet, damit ein Klick (der zugleich
        Highlight + Select feuert) keine zwei gestapelten Dialoge erzeugt.
        """
        self._favorites_mode = False
        if not self._custom_seed:
            if allow_dialog:
                self.action_edit_seed()
            return
        if not self._seed_mode:
            self._seed_mode = True
            self.sub_title = f"seed: {self._custom_seed}"
            self._log_event(f"seed mode [b]{self._custom_seed}[/b]")
        self._ensure_seed_recipes()
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
        if self._favorites_mode:
            self.notify("Favorites can't be regenerated", severity="warning")
            return
        if self._seed_mode and not self._custom_seed:
            self.action_edit_seed()
            return
        self._fresh_recipes()
        self._log_event("regenerated")
        # Effekt zuerst spielen (vor _rerender), damit die animierten Namen
        # genau den Namen entsprechen, die anschliessend in der Tabelle stehen.
        self._play_regenerate_effect()
        self._rerender()

    def _play_regenerate_effect(self) -> None:
        """Spielt den ausgewaehlten tte-Effekt auf den frisch generierten Namen.

        Berechnet die neuen Vorschlaege (ohne Tabellen-Update), reicht ihre
        Namen an die tte-Animation und gibt das Terminal waehrend des Effekts
        via `App.suspend()` frei - Textual rendert solange nicht.
        """
        if self._effect_name == EFFECT_NONE:
            return
        names = self._compute_current_names()
        if not names:
            return
        text = "\n".join(names)
        try:
            with self.suspend():
                play_effect(text, self._effect_name)
        except Exception as exc:
            # Effekte sind reines Eye-Candy - bei Fehlern still weiterlaufen,
            # aber im Log hinterlassen, damit der User es findet.
            self._log_event(f"[red]effect failed: {exc}[/red]")

    def _compute_current_names(self) -> list[str]:
        """Berechnet die Namen, die ein anschliessendes _rerender erzeugen wuerde.

        Wir koennen nicht einfach die Tabelle abfragen - sie zeigt noch die
        VORHERIGE Generation. Stattdessen rendern wir die aktuellen Recipes
        einmal in Memory, ohne die Suggestion-Liste oder die Tabelle anzufassen.
        """
        if self._seed_mode and self._custom_seed:
            theme = self.generator.seeded_theme(self._custom_seed)
            recipes = self._recipes.get(CUSTOM_SEED_SLUG, [])
        elif self.theme_slug:
            theme = self.generator.themes[self.theme_slug]
            recipes = self._recipes.get(self.theme_slug, [])
        else:
            return []
        mutation = self.mutation_percent / 100.0
        return [
            self.generator.render(r, theme, self.word_count, mutation).name for r in recipes
        ]

    def action_edit_seed(self) -> None:
        """Oeffnet den Eingabedialog fuer den Custom Seed."""
        # Doppelschutz: falls bereits ein Modal offen ist (z.B. der Dialog
        # selbst), nicht erneut pushen - sonst stapeln sich zwei.
        if len(self.screen_stack) > 1:
            return
        self.push_screen(
            TextInputScreen(
                title="Custom Seed",
                prompt="Your idea (e.g. \"Sitemap\" or \"Link\"):",
                initial=self._custom_seed,
                placeholder="Sitemap",
                validator=lambda s: None if s.strip() else "Please enter a word.",
                lang="en",
            ),
            callback=self._on_seed_entered,
        )

    def _on_seed_entered(self, raw: str | None) -> None:
        """Speichert den eingegebenen Seed und rendert die Vorschlaege."""
        if raw is None:
            # Abbruch - wenn vorher kein Seed existierte und der User noch
            # nicht im Seed-Mode war, einfach nichts tun.
            return
        seed = raw.strip()
        if not seed:
            return
        changed = seed != self._custom_seed
        self._custom_seed = seed
        if changed:
            # Neuer Seed => alte Recipes verwerfen.
            self._recipes.pop(CUSTOM_SEED_SLUG, None)
            # Label in der Theme-Liste aktualisieren.
            self._refresh_seed_label()
        self._seed_mode = True
        self._favorites_mode = False
        self.sub_title = f"seed: {seed}"
        self._log_event(f"seed -> [b]{seed}[/b]")
        self._save_settings()
        self._ensure_seed_recipes()
        self._rerender()

    def _refresh_seed_label(self) -> None:
        """Aktualisiert den 'Custom Seed: <seed>'-Eintrag in der Theme-Liste."""
        try:
            seed_item = self.query_one(f"#{self.CUSTOM_SEED_ITEM_ID}", ListItem)
        except Exception:
            return
        label = f"Custom Seed: {self._custom_seed}" if self._custom_seed else "Custom Seed"
        for child in seed_item.query(Static):
            child.update(label)
            break

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
        is_special = self._favorites_mode or self._seed_mode
        if not is_special and not self.generator.themes[self.theme_slug].mutate:
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

    def on_select_changed(self, event: Select.Changed) -> None:
        """Verarbeitet die Auswahl im Effekt-Dropdown."""
        if event.select.id != "effect-select":
            return
        new_value = str(event.value) if event.value is not None else EFFECT_NONE
        if not is_valid_effect(new_value) or new_value == self._effect_name:
            return
        self._effect_name = new_value
        self._log_event(f"effect -> [b]{new_value}[/b]")
        self._save_settings()

    def on_slider_changed(self, event: Slider.Changed) -> None:
        new_value = int(event.value)
        # In der Favoriten-Ansicht sind Words/Suggestions gesperrt.
        if self._favorites_mode and event.slider.id != "mutation-slider":
            return
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
        elif event.slider.id == "count-slider":
            if new_value == self.suggestion_count:
                return
            self.suggestion_count = new_value
            self._log_event(f"suggestions -> [b]{new_value}[/b]")
            # Recipe-Cache aller Themes verwerfen - die Anzahl hat sich
            # geaendert, vorhandene Recipes passen nicht mehr.
            self._recipes.clear()
            self._ensure_recipes()
            self._ensure_seed_recipes()
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
        if self._favorites_mode:
            self._remove_favorite_at_cursor()
            return
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

    def _remove_favorite_at_cursor(self) -> None:
        """Entfernt den Favoriten in der Cursor-Zeile (nur Favoriten-Ansicht)."""
        table = self.query_one("#suggestions", DataTable)
        row = table.cursor_row
        if not 0 <= row < len(self.favorites):
            return
        removed = self.favorites.pop(row)
        self.notify(f"Removed favorite: {removed.name}")
        self._log_event(f"unfav [b]{removed.name}[/b]")
        self._save_settings()
        self._rerender()

    def action_open_favorites(self) -> None:
        self.push_screen(FavoritesScreen(self.favorites))

    def action_add_custom_favorite(self) -> None:
        """Oeffnet einen Eingabedialog, um einen eigenen Namen als Favorit zu speichern."""
        self.push_screen(
            TextInputScreen(
                title="Add custom idea",
                prompt="Codename to save as favorite:",
                placeholder="e.g. Sitemap Pioneer",
                validator=self._validate_custom_favorite,
                lang="en",
            ),
            callback=self._on_custom_favorite_entered,
        )

    def _validate_custom_favorite(self, raw: str) -> str | None:
        """Pruefung fuer den Eingabedialog: nicht leer, kein Duplikat."""
        text = raw.strip()
        if not text:
            return "Please enter a name."
        slug = _slugify_name(text)
        if not slug:
            return "Name must contain at least one letter or digit."
        if any(f.slug == slug for f in self.favorites):
            return "A favorite with this name already exists."
        return None

    def _on_custom_favorite_entered(self, raw: str | None) -> None:
        """Fuegt den eingegebenen Namen als Favorit hinzu und persistiert."""
        if raw is None:
            return
        name = raw.strip()
        if not name:
            return
        slug = _slugify_name(name)
        if not slug:
            return
        suggestion = Suggestion(
            name=name,
            slug=slug,
            pattern=Pattern.THEME_ONLY,
            mutated=False,
            source_words=(name,),
        )
        self.favorites.append(suggestion)
        self.notify(f"Added favorite: {name}")
        self._log_event(f"fav [b]{name}[/b]")
        self._save_settings()
        if self._favorites_mode:
            self._rerender()
        else:
            self._update_info()

    def action_about(self) -> None:
        self.push_screen(AboutScreen())

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Blendet Aktionen im Footer aus, wenn sie im aktuellen Modus keinen Sinn ergeben."""
        # ModalScreen-Isolation: bei offenem Modal alle App-Shortcuts abschalten.
        if len(self.screen_stack) > 1:
            return None
        if action == "add_custom_favorite" and not self._favorites_mode:
            # "+" gibt es nur in der Favoriten-Ansicht.
            return None
        return True

    def on_suggestions_table_right_clicked(
        self, event: SuggestionsTable.RightClicked
    ) -> None:
        """Oeffnet das Kontextmenue fuer die rechtsgeklickte Vorschlagszeile."""
        if len(self.screen_stack) > 1:
            return
        if not 0 <= event.row < len(self.suggestions):
            return
        suggestion = self.suggestions[event.row]
        is_fav = self._favorites_mode or any(
            f.slug == suggestion.slug for f in self.favorites
        )
        items = [
            ContextMenuItem("copy_slug", "Copy slug", shortcut="c"),
            ContextMenuItem("copy_name", "Copy name", shortcut="n"),
            ContextMenuItem.separator(),
            ContextMenuItem(
                "toggle_favorite",
                "Remove favorite" if is_fav else "Add favorite",
                icon="★" if is_fav else "☆",
                shortcut="f",
            ),
        ]
        if self._favorites_mode:
            # In der Favoriten-Ansicht: manuellen Idea-Eintrag hinzufuegen.
            items.append(ContextMenuItem.separator())
            items.append(
                ContextMenuItem("add_custom_favorite", "Add custom idea...", shortcut="+")
            )
        else:
            # "Regenerate" gibt es nur fuer echte Themes/Custom-Seed.
            items.append(ContextMenuItem.separator())
            items.append(ContextMenuItem("regenerate", "Regenerate all", shortcut="r"))
        self.push_screen(
            ContextMenuScreen(items, at=(event.screen_x, event.screen_y)),
            callback=self._on_context_action,
        )

    def _on_context_action(self, action_id: str | None) -> None:
        """Fuehrt die im Kontextmenue gewaehlte Aktion aus."""
        if action_id == "copy_slug":
            self.action_copy_slug()
        elif action_id == "copy_name":
            self.action_copy_name()
        elif action_id == "toggle_favorite":
            self.action_toggle_favorite()
        elif action_id == "regenerate":
            self.action_regenerate()
        elif action_id == "add_custom_favorite":
            self.action_add_custom_favorite()


def _reset_mouse_tracking() -> None:
    """Schaltet Maus-Tracking nach App-Ende explizit ab.

    Unter Windows laesst Textuals Teardown gelegentlich Maus-Tracking-Modi
    aktiv - danach landet bei jeder Mausbewegung Steuerzeichen-Muell
    (z.B. `[555;114;57M`) in der Shell. Dieser Reset ist idempotent: sind
    die Modi bereits aus, bewirken die Sequenzen nichts.
    """
    if not sys.stdout.isatty():
        return
    # ?1000/?1002/?1003 = Maus-Tracking-Modi, ?1006/?1015 = erweitertes Encoding
    sys.stdout.write("\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l\x1b[?1015l")
    sys.stdout.flush()


def run_tui() -> None:
    try:
        CodenameApp().run()
    finally:
        _reset_mouse_tracking()


__all__ = ["RANDOM_THEME_SLUG", "CodenameApp", "run_tui"]
