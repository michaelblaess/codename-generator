from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

from codename_generator.favorites import (
    favorite_to_dict,
    merge_favorites,
    parse_favorites,
    read_import,
    write_export,
)
from codename_generator.generator import (
    FILTER_POOL_FACTOR,
    AnchorPosition,
    Generator,
    Method,
    Presented,
    PresentOptions,
    StackRequest,
    normalize_letters,
)
from codename_generator.scoring import NameFilter
from codename_generator.settings import JsonSettingsStore
from codename_generator.wordlist import NEUTRAL_LANGUAGE, TONES

# Mutationswahrscheinlichkeit, wenn weder Aufruf noch Theme etwas vorgeben.
DEFAULT_MUTATION_CHANCE = 0.35


def _mutation_chance(theme_default: int | None, requested: float | None) -> float:
    """Bestimmt die Mutationswahrscheinlichkeit: Aufruf vor Theme vor Default."""
    if requested is not None:
        return requested
    if theme_default is not None:
        return theme_default / 100.0
    return DEFAULT_MUTATION_CHANCE


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codename",
        description="Generate project codenames from curated themes.",
    )
    parser.add_argument(
        "--theme",
        "-t",
        help=(
            "Theme slug (e.g. greek-gods, flowers). Omit to launch TUI. "
            "With --word the theme becomes the partner of your word."
        ),
    )
    parser.add_argument(
        "--word",
        "-w",
        default=None,
        help='Your own word (e.g. "Sitemap"), combined with modifiers or with --theme',
    )
    parser.add_argument(
        "--position",
        choices=[p.value for p in AnchorPosition],
        default=AnchorPosition.ANY.value,
        help="Where your --word stands in the name (default: any)",
    )
    parser.add_argument(
        "--mix",
        default=None,
        help=(
            "Second theme: crossed with --theme (one word from each), learned from with "
            "--method coined, the back half with --method blend"
        ),
    )
    parser.add_argument(
        "--method",
        choices=[m.value for m in Method],
        default=Method.WORDS.value,
        help=(
            "How names are made: words (theme words with modifiers), coined (new words that "
            "sound like the theme), blend (two theme words melted), acronym (see --letters)"
        ),
    )
    parser.add_argument("--letters", default="", help="Acronym letters, up to three (e.g. SMT)")
    parser.add_argument("--tone", choices=TONES, default=None, help="Only modifiers of this mood")
    parser.add_argument("--initial", default="", help="Only names starting with these letters")
    parser.add_argument(
        "--max-syllables", type=int, default=0, help="Only names with at most this many syllables"
    )
    parser.add_argument(
        "--alliteration", action="store_true", help="Only names whose words share the initial"
    )
    parser.add_argument(
        "--sort", action="store_true", help="Sort by sound score (short, easy to say and spell)"
    )
    parser.add_argument(
        "--export-favorites",
        metavar="FILE",
        default=None,
        help="Write the TUI favorites to FILE (JSON, readable by the web version)",
    )
    parser.add_argument(
        "--import-favorites",
        metavar="FILE",
        default=None,
        help="Add favorites from FILE (a web export or another settings.json)",
    )
    parser.add_argument("--count", "-n", type=int, default=30, help="How many suggestions")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--mutation-chance",
        type=float,
        default=None,
        help=(
            "0..1 probability a suggestion uses phonetic mutation "
            f"(default: the theme's own value, else {DEFAULT_MUTATION_CHANCE})"
        ),
    )
    parser.add_argument(
        "--words",
        type=int,
        default=2,
        choices=(1, 2, 3),
        help="Exact number of name components (1-3)",
    )
    parser.add_argument("--list-themes", action="store_true")
    parser.add_argument(
        "--lang",
        "-L",
        default=None,
        help="Language for neutral themes and for --list-themes (e.g. en, de)",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()

    # In einer Pipe schreibt Python unter Windows cp1252 - "Stürzender" kam
    # dann als "St?rzender" an (belegt am 23.09.2026). Die Namen sind UTF-8.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")

    if args.export_favorites is not None:
        return _export_favorites(Path(args.export_favorites))
    if args.import_favorites is not None:
        return _import_favorites(Path(args.import_favorites))

    if args.word is not None:
        return _print_anchored(args)

    if args.list_themes or args.theme is None:
        if args.theme is None and not args.list_themes:
            from codename_generator.tui import run_tui

            run_tui()
            return 0
        gen = Generator.load(seed=args.seed)
        for slug, theme in gen.themes.items():
            if args.lang and theme.language not in (args.lang, NEUTRAL_LANGUAGE):
                continue
            print(f"{slug:24s}  [{theme.language}]  {theme.name} ({len(theme.words)} words)")
        return 0

    return _print_theme(args)


def _print_theme(args: argparse.Namespace) -> int:
    """Themenansicht: Methode, Mix, Ton, Filter und Sortierung wie in der TUI."""
    gen = Generator.load(seed=args.seed)
    selected = gen.themes.get(args.theme)
    partner = gen.themes.get(args.mix) if args.mix is not None else None
    if selected is None or (args.mix is not None and partner is None):
        print(
            f"Error: unknown theme {args.theme if selected is None else args.mix!r}",
            file=sys.stderr,
        )
        return 2
    method = Method(args.method)
    if method == Method.ACRONYM and not normalize_letters(args.letters):
        print("Error: --method acronym needs --letters (e.g. SMT)", file=sys.stderr)
        return 2
    name_filter = _name_filter(args)
    stack = gen.build_stack(
        StackRequest(
            theme=selected,
            count=args.count * FILTER_POOL_FACTOR if name_filter.active else args.count,
            language=args.lang,
            method=method,
            partner=partner,
            tone=args.tone or "",
            letters=args.letters,
            alliterate=name_filter.alliteration,
        )
    )
    # Beim Mix gilt der Mutationswert des zweiten Themes - von ihm kommt das mutierte Wort.
    source = partner if partner is not None and method == Method.WORDS else selected
    chance = _mutation_chance(source.default_mutation, args.mutation_chance)
    options = PresentOptions(args.words, chance, args.lang, name_filter, args.sort, args.count)
    _print_suggestions(gen.present(stack.recipes, stack.theme, options), with_score=args.sort)
    return 0


def _name_filter(args: argparse.Namespace) -> NameFilter:
    return NameFilter(
        initial=str(args.initial).strip(),
        max_syllables=max(0, int(args.max_syllables)),
        alliteration=bool(args.alliteration),
    )


def _print_suggestions(shown: list[Presented], *, with_score: bool = False) -> None:
    for i, item in enumerate(shown, 1):
        s = item.suggestion
        flag = " *" if s.mutated else "  "
        score = f"{item.score:3d}  " if with_score else ""
        print(f"{i:2d}.{flag} {score}{s.name:30s} {s.slug}")


def _export_favorites(path: Path) -> int:
    favorites = parse_favorites(JsonSettingsStore().load())
    try:
        write_export(path, favorites)
    except OSError as exc:
        print(f"Error: cannot write {path}: {exc}", file=sys.stderr)
        return 2
    print(f"{len(favorites)} favorites written to {path}")
    return 0


def _import_favorites(path: Path) -> int:
    try:
        incoming = read_import(path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error: cannot read {path}: {exc}", file=sys.stderr)
        return 2
    if not incoming:
        print(f"Error: no favorites found in {path}", file=sys.stderr)
        return 2
    store = JsonSettingsStore()
    settings = store.load()
    merged, added = merge_favorites(parse_favorites(settings), incoming)
    settings["favorites"] = [favorite_to_dict(f) for f in merged]
    store.save(settings)
    print(f"{added} new favorites imported, {len(incoming) - added} already there")
    return 0


def _print_anchored(args: argparse.Namespace) -> int:
    """Eigenes Wort mit Zusaetzen, oder mit --theme als Partner-Thema."""
    word = str(args.word).strip()
    if not word:
        print("Error: --word must not be empty", file=sys.stderr)
        return 2
    gen = Generator.load(seed=args.seed)
    position = AnchorPosition(args.position)
    language = args.lang or "en"
    name_filter = _name_filter(args)
    count = args.count * FILTER_POOL_FACTOR if name_filter.active else args.count
    if args.theme is None:
        theme = gen.seeded_theme(word, language, position)
        recipes = gen.generate_seeded_recipes(
            word, count, language, position, args.tone or "", name_filter.alliteration
        )
        chance = _mutation_chance(None, args.mutation_chance)
    else:
        partner = gen.themes.get(args.theme)
        if partner is None:
            print(f"Error: unknown theme {args.theme!r}", file=sys.stderr)
            return 2
        theme = gen.anchored_theme(word, partner, language, position)
        recipes = gen.generate_anchored_recipes(word, partner, count, position)
        chance = _mutation_chance(partner.default_mutation, args.mutation_chance)
    options = PresentOptions(args.words, chance, language, name_filter, args.sort, args.count)
    _print_suggestions(gen.present(recipes, theme, options), with_score=args.sort)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
