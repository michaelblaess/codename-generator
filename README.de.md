# codename-generator

<p align="center">
  <img src="docs/flags/gb.svg" height="13" alt=""> <a href="README.md">English</a> ·
  <img src="docs/flags/de.svg" height="13" alt=""> <b>Deutsch</b>
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
[![Themes](https://img.shields.io/badge/themes-18-yellow)](src/codename_generator/data/themes)

Ein Codename-Generator für das Terminal. Wähle ein Thema (griechische Götter, Rennpferde, Edelsteine, Whisky, ...) und erhalte einen Stapel einzigartiger Vorschläge (10 bis 40, frei wählbar), kombiniert mit Adjektiv- oder Verb-Modifikatoren und optionalen phonetischen Mutationen.

## Themen

Griechische Götter · Ägyptische Götter · Nordische Götter · Sternbilder · Tierkreiszeichen · Tiere · Rennpferde · Blumen · Edelsteine · Weine · Whisky · Berge · Pilze · Historische Schiffe · Wahrzeichen · Dev · Random (gepoolt)

Zwei Themen nutzen ihre eigenen kuratierten Wort-Pools:

- **Evocative** - ein markantes Adjektiv + ein emotional aufgeladenes Substantiv
  (`Cold Ember`, `Iron Hour`, `Sacred Tide`). Wird nie mutiert.
- **Power words** - einzelne, kraftvolle, eigenständige Wörter, keine Modifikatoren
  (`Mythos`, `Skyline`, `Oracle`, `Aegis`).

Ein Theme-YAML kann die globalen Modifikator-Pools (`adjectives`, `verbs`)
überschreiben, die Namens-`patterns` einschränken, die Mutation deaktivieren
(`mutate: false`) oder den Start-Mutationswert setzen (`default_mutation`).

## Einrichtung

```
setup.bat        # Windows
./setup.sh       # macOS/Linux
```

Benötigt [uv](https://docs.astral.sh/uv/).

## Verwendung

### TUI (Standard)

```
run.bat          # Windows
./run.sh         # macOS/Linux
uv run codename  # jede Plattform
```

Tasten: `r` neu generieren · `c` Slug kopieren · `n` Name kopieren · `m` Mutation +25% · `t` Thema wechseln · `f` Favorit · `v` Favoriten anzeigen · `a` Info · `q` beenden

Das linke Einstellungspanel hat drei Schieberegler: **Mutationswahrscheinlichkeit**
(0-100%), **Wortanzahl** (1, 2 oder 3 sichtbare Wörter pro Name) und
**Vorschläge** (10/20/30/40 Namen pro Stapel). Das Verschieben eines Reglers
rendert den *aktuellen* Satz von Namen direkt neu, sodass du den Effekt sofort
siehst — nur `r` zieht einen frischen Stapel. Jedes Thema behält seinen
eigenen Satz, sodass das Hin- und Herwechseln zwischen Themen nie verliert, was
du hattest. Bewege den Mauszeiger über ein Thema in der Liste für einen
Tooltip mit Beschreibung. Rechtsklick auf einen Vorschlag öffnet ein
Kontextmenü (Slug/Name kopieren, Favorit, neu generieren). Die Theme-Liste
beginnt mit einem **Favorites**-Eintrag — wählst du ihn, erscheinen rechts
deine gespeicherten Favoriten, wo nur der Mutations-Regler wirkt und sie live
neu mutiert. Wird mit 35+ Farb-Themes ausgeliefert (Textual-Builtins plus
Retro-Paletten) — wechseln mit `t` oder dem Ctrl+P-Theme-Picker. Gewähltes
Farb-Theme, Mutationswahrscheinlichkeit, Wortanzahl, Vorschlagsanzahl und
Favoriten werden in `~/.codename-generator/settings.json` über Neustarts
hinweg gespeichert.

### CLI

```
uv run codename --list-themes
uv run codename -t greek-gods           # 30 suggestions (default)
uv run codename -t flowers -n 5 --mutation-chance 0.6 --seed 42
uv run codename -t random -n 20         # pulls from every theme
uv run codename -t whisky --words 3     # exactly 3 components per name
```

Ein `*` neben einem Vorschlag bedeutet, dass eine phonetische Mutation angewendet wurde
(`Pegasus -> Pegasos`, `Carnation -> Carnatiyn`, `Frankel -> Frankil`).

## Themen hinzufügen

Lege eine YAML-Datei in `src/codename_generator/data/themes/` ab:

```yaml
name: My Theme
description: ...
words:
  - Word1
  - Word2
```

## Danksagung

Die Einstellungs-Schieberegler nutzen [textual-slider](https://github.com/TomJGooding/textual-slider)
von [Tom J Gooding](https://github.com/TomJGooding) - danke für das Widget.

## Lizenz

Apache License 2.0 - siehe [LICENSE](LICENSE).
