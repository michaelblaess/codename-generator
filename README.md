# codename-generator

[![Stars](https://img.shields.io/github/stars/michaelblaess/codename-generator?style=for-the-badge&logo=github&logoColor=white&labelColor=1e2228&color=fbbf24)](https://github.com/michaelblaess/codename-generator/stargazers)
[![Forks](https://img.shields.io/github/forks/michaelblaess/codename-generator?style=for-the-badge&logo=github&logoColor=white&labelColor=1e2228&color=34d399)](https://github.com/michaelblaess/codename-generator/network/members)
[![Issues](https://img.shields.io/github/issues/michaelblaess/codename-generator?style=for-the-badge&logo=github&logoColor=white&labelColor=1e2228&color=f87171)](https://github.com/michaelblaess/codename-generator/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/michaelblaess/codename-generator?style=for-the-badge&logo=github&logoColor=white&labelColor=1e2228&color=a78bfa)](https://github.com/michaelblaess/codename-generator/pulls)

[![Last Commit](https://img.shields.io/github/last-commit/michaelblaess/codename-generator?style=for-the-badge&logo=git&logoColor=white&labelColor=1e2228&color=3b82f6)](https://github.com/michaelblaess/codename-generator/commits/main)
[![CI](https://img.shields.io/github/actions/workflow/status/michaelblaess/codename-generator/ci.yml?branch=main&style=for-the-badge&logo=githubactions&logoColor=white&labelColor=1e2228&color=3b82f6&label=CI)](https://github.com/michaelblaess/codename-generator/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache_2.0-3b82f6?style=for-the-badge&labelColor=1e2228)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.13-3b82f6?style=for-the-badge&logo=python&logoColor=white&labelColor=1e2228)](https://www.python.org/)
[![Themes](https://img.shields.io/badge/themes-14-fbbf24?style=for-the-badge&labelColor=1e2228)](src/codename_generator/data/themes)

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

Keys: `r` regenerate · `c` copy slug · `n` copy name · `m` bump mutation +25% · `t` cycle Textual theme · `f` favorite · `F` show favorites · `a` about · `q` quit

The mutation chance is also adjustable via a slider in the top bar.

### CLI

```
uv run codename --list-themes
uv run codename -t greek-gods           # 30 suggestions (default)
uv run codename -t flowers -n 5 --mutation-chance 0.6 --seed 42
uv run codename -t random -n 20         # pulls from every theme
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

## License

Apache License 2.0 - see [LICENSE](LICENSE).
