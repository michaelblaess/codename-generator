from __future__ import annotations

import argparse
import io
import sys

from codename_generator.generator import AnchorPosition, Generator, Suggestion
from codename_generator.wordlist import NEUTRAL_LANGUAGE

# Mutationswahrscheinlichkeit, wenn weder Aufruf noch Theme etwas vorgeben.
DEFAULT_MUTATION_CHANCE = 0.35


def _mutation_chance(theme_default: int | None, requested: float | None) -> float:
    """Bestimmt die Mutationswahrscheinlichkeit: Aufruf vor Theme vor Default."""
    if requested is not None:
        return requested
    if theme_default is not None:
        return theme_default / 100.0
    return DEFAULT_MUTATION_CHANCE


def main() -> int:
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
        help="Cross --theme with a second theme: one word from each (e.g. Taurus Orion)",
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
    args = parser.parse_args()

    # In einer Pipe schreibt Python unter Windows cp1252 - "Stürzender" kam
    # dann als "St?rzender" an (belegt am 23.09.2026). Die Namen sind UTF-8.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")

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

    gen = Generator.load(seed=args.seed)
    selected = gen.themes.get(args.theme)
    if args.mix is not None:
        second = gen.themes.get(args.mix)
        if selected is None or second is None:
            print(
                f"Error: unknown theme {args.theme if selected is None else args.mix!r}",
                file=sys.stderr,
            )
            return 2
        crossed = gen.crossed_theme(selected, second, args.lang)
        chance = _mutation_chance(second.default_mutation, args.mutation_chance)
        recipes = gen.generate_crossed_recipes(selected, second, args.count)
        _print_suggestions([gen.render(r, crossed, 2, chance, args.lang) for r in recipes])
        return 0
    try:
        suggestions = gen.suggest(
            theme_slug=args.theme,
            count=args.count,
            mutation_chance=_mutation_chance(
                selected.default_mutation if selected else None, args.mutation_chance
            ),
            word_count=args.words,
            language=args.lang,
        )
    except KeyError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    _print_suggestions(suggestions)
    return 0


def _print_suggestions(suggestions: list[Suggestion]) -> None:
    for i, s in enumerate(suggestions, 1):
        flag = " *" if s.mutated else "  "
        print(f"{i:2d}.{flag} {s.name:30s} {s.slug}")


def _print_anchored(args: argparse.Namespace) -> int:
    """Eigenes Wort mit Zusaetzen, oder mit --theme als Partner-Thema."""
    word = str(args.word).strip()
    if not word:
        print("Error: --word must not be empty", file=sys.stderr)
        return 2
    gen = Generator.load(seed=args.seed)
    position = AnchorPosition(args.position)
    language = args.lang or "en"
    if args.theme is None:
        theme = gen.seeded_theme(word, language, position)
        recipes = gen.generate_seeded_recipes(word, args.count, language, position)
        chance = _mutation_chance(None, args.mutation_chance)
    else:
        partner = gen.themes.get(args.theme)
        if partner is None:
            print(f"Error: unknown theme {args.theme!r}", file=sys.stderr)
            return 2
        theme = gen.anchored_theme(word, partner, language, position)
        recipes = gen.generate_anchored_recipes(word, partner, args.count, position)
        chance = _mutation_chance(partner.default_mutation, args.mutation_chance)
    _print_suggestions([gen.render(r, theme, args.words, chance, language) for r in recipes])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
