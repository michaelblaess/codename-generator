from __future__ import annotations

import argparse
import sys

from codename_generator.generator import Generator


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
        default=0.35,
        help="0..1 probability a suggestion uses phonetic mutation",
    )
    parser.add_argument("--list-themes", action="store_true")
    args = parser.parse_args()

    if args.list_themes or args.theme is None:
        if args.theme is None and not args.list_themes:
            from codename_generator.tui import run_tui

            run_tui()
            return 0
        gen = Generator.load(seed=args.seed)
        for slug, theme in gen.themes.items():
            print(f"{slug:24s}  {theme.name} ({len(theme.words)} words)")
        return 0

    gen = Generator.load(seed=args.seed)
    try:
        suggestions = gen.suggest(
            theme_slug=args.theme,
            count=args.count,
            mutation_chance=args.mutation_chance,
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
