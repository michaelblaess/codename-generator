from __future__ import annotations

import argparse
import sys

from codename_generator.generator import Generator
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
        help="Theme slug (e.g. greek-gods, flowers). Omit to launch TUI.",
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

    for i, s in enumerate(suggestions, 1):
        flag = " *" if s.mutated else "  "
        print(f"{i:2d}.{flag} {s.name:30s} {s.slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
