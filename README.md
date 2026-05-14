# codename-generator

Project codename generator with curated themes and phonetic mutations.

## Themes

- Greek gods
- Egyptian gods
- Norse gods
- Constellations
- Racehorses
- Flowers
- Gemstones

## Usage

### TUI (default)

```
uv run codename
```

Keys: `r` regenerate, `c` copy slug, `n` copy name, `m` cycle mutation chance, `t` cycle Textual theme, `f` toggle favorite, `F` show favorites, `q` quit.

### CLI

```
uv run codename --list-themes
uv run codename -t greek-gods -n 10
uv run codename -t flowers -n 5 --mutation-chance 0.6 --seed 42
```

A `*` next to a suggestion means a phonetic mutation was applied (e.g. Pegasus -> Pegasos, Carnation -> Carnatiyn).

## Adding themes

Drop a YAML file into `src/codename_generator/data/themes/`:

```yaml
name: My Theme
description: ...
words:
  - Word1
  - Word2
```
