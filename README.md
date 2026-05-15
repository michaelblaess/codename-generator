# codename-generator

<p align="center">
  <img src="docs/flags/gb.svg" height="13" alt=""> <b>English</b> ·
  <img src="docs/flags/de.svg" height="13" alt=""> <a href="README.de.md">Deutsch</a>
</p>

---

[![Stars](https://img.shields.io/github/stars/michaelblaess/codename-generator?logo=github&logoColor=white&color=yellow)](https://github.com/michaelblaess/codename-generator/stargazers)
[![Forks](https://img.shields.io/github/forks/michaelblaess/codename-generator?logo=github&logoColor=white&color=brightgreen)](https://github.com/michaelblaess/codename-generator/network/members)
[![Issues](https://img.shields.io/github/issues/michaelblaess/codename-generator?logo=github&logoColor=white&color=red)](https://github.com/michaelblaess/codename-generator/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/michaelblaess/codename-generator?logo=github&logoColor=white&color=blueviolet)](https://github.com/michaelblaess/codename-generator/pulls)
[![Last Commit](https://img.shields.io/github/last-commit/michaelblaess/codename-generator?logo=git&logoColor=white)](https://github.com/michaelblaess/codename-generator/commits/main)
[![CI](https://github.com/michaelblaess/codename-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/michaelblaess/codename-generator/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.13-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Themes](https://img.shields.io/badge/themes-17-yellow)](src/codename_generator/data/themes)

A terminal codename generator. Pick a theme (Greek gods, racehorses, gemstones, whisky, ...), get 30 unique suggestions combined with adjective or verb modifiers and optional phonetic mutations.

## Themes

Greek gods · Egyptian gods · Norse gods · Constellations · Zodiac · Racehorses · Flowers · Gemstones · Wines · Whisky · Mountains · Mushrooms · Historic ships · Landmarks · Dev · Random (pooled)

Two themes use their own curated word pools:

- **Evocative** - a stark adjective + an emotionally charged noun
  (`Cold Ember`, `Iron Hour`, `Sacred Tide`). Never mutated.
- **Power words** - single bold standalone words, no modifiers
  (`Mythos`, `Skyline`, `Oracle`, `Aegis`).

A theme YAML can override the global modifier pools (`adjectives`, `verbs`),
restrict `patterns`, allow bare unmutated words (`bare: true`) or disable
mutation (`mutate: false`).

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
**word count** (exactly 1, 2 or 3 components per name). Moving a slider
re-renders the *current* set of names in place so you see the effect
immediately — only `r` draws a fresh batch. Each theme keeps its own set, so
switching themes back and forth never loses what you had. Hover a theme in the
list for a tooltip describing it. Ships with 35+ themes (Textual built-ins
plus retro palettes) — switch with `t` or the Ctrl+P theme picker. Chosen
theme, mutation chance, word count and favorites are persisted to
`~/.codename-generator/settings.json` across restarts.

### CLI

```
uv run codename --list-themes
uv run codename -t greek-gods           # 30 suggestions (default)
uv run codename -t flowers -n 5 --mutation-chance 0.6 --seed 42
uv run codename -t random -n 20         # pulls from every theme
uv run codename -t whisky --words 3     # exactly 3 components per name
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
