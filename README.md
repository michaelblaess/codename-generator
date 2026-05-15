# codename-generator

[![Stars](https://img.shields.io/github/stars/michaelblaess/codename-generator?logo=github&logoColor=white&color=yellow)](https://github.com/michaelblaess/codename-generator/stargazers)
[![Forks](https://img.shields.io/github/forks/michaelblaess/codename-generator?logo=github&logoColor=white&color=brightgreen)](https://github.com/michaelblaess/codename-generator/network/members)
[![Issues](https://img.shields.io/github/issues/michaelblaess/codename-generator?logo=github&logoColor=white&color=red)](https://github.com/michaelblaess/codename-generator/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/michaelblaess/codename-generator?logo=github&logoColor=white&color=blueviolet)](https://github.com/michaelblaess/codename-generator/pulls)
[![Last Commit](https://img.shields.io/github/last-commit/michaelblaess/codename-generator?logo=git&logoColor=white)](https://github.com/michaelblaess/codename-generator/commits/main)
[![CI](https://github.com/michaelblaess/codename-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/michaelblaess/codename-generator/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.13-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Themes](https://img.shields.io/badge/themes-14-yellow)](src/codename_generator/data/themes)

A terminal codename generator. Pick a theme (Greek gods, racehorses, gemstones, whisky, ...), get 30 unique suggestions combined with adjective or verb modifiers and optional phonetic mutations.

## Themes

Greek gods · Egyptian gods · Norse gods · Constellations · Racehorses · Flowers · Gemstones · Wines · Whisky · Mountains · Mushrooms · Historic ships · Landmarks · Random (pooled)

## Setup

```
setup.bat        # Windows
./setup.sh       # macOS/Linux
```

Requires [uv](https://docs.astral.sh/uv/).

## Usage

### TUI (default)

```
run.bat          # Windows
./run.sh         # macOS/Linux
uv run codename  # any platform
```

Keys: `r` regenerate · `c` copy slug · `n` copy name · `m` bump mutation +25% · `t` cycle theme · `f` favorite · `v` view favorites · `a` about · `q` quit

The left settings panel has two sliders: **mutation chance** (0-100%) and
**word count** (1-3 components per name). Ships with 35+ themes (Textual
built-ins plus retro palettes) — switch with `t` or the Ctrl+P theme picker.
Chosen theme, mutation chance, word count and favorites are persisted to
`~/.codename-generator/settings.json` across restarts.

### CLI

```
uv run codename --list-themes
uv run codename -t greek-gods           # 30 suggestions (default)
uv run codename -t flowers -n 5 --mutation-chance 0.6 --seed 42
uv run codename -t random -n 20         # pulls from every theme
uv run codename -t whisky --max-words 2 # at most 2 components per name
```

A `*` next to a suggestion means a phonetic mutation was applied
(`Pegasus -> Pegasos`, `Carnation -> Carnatiyn`, `Frankel -> Frankil`).

## Adding themes

Drop a YAML file into `src/codename_generator/data/themes/`:

```yaml
name: My Theme
description: ...
words:
  - Word1
  - Word2
```

## Credits

The settings sliders use [textual-slider](https://github.com/TomJGooding/textual-slider)
by [Tom J Gooding](https://github.com/TomJGooding) - thank you for the widget.

## License

Apache License 2.0 - see [LICENSE](LICENSE).
