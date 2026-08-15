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
[![Themes](https://img.shields.io/badge/themes-23-yellow)](src/codename_generator/data/themes)

Ein Codename-Generator für das Terminal. Wähle ein Thema (griechische Götter, Rennpferde, Edelsteine, Whisky, ...) und erhalte einen Stapel einzigartiger Vorschläge (10 bis 40, frei wählbar), kombiniert mit Adjektiv- oder Verb-Modifikatoren und optionalen phonetischen Mutationen.

## Themen

Griechische Götter · Ägyptische Götter · Nordische Götter · Sternbilder · Tierkreiszeichen · Tiere · Gefährliche Tiere · Rennpferde · Blumen · Edelsteine · Weine · Whisky · Berge · Pilze · Historische Schiffe · Wahrzeichen · Swatch-Uhren · Dev · Random (gepoolt)

Deutsche Themen (`language: de`): Tierwelt · Sagenwesen · Wetter und Landschaft · Random (DE)

Themen, deren Wörter Eigennamen sind (griechische/ägyptische/nordische Götter,
Rennpferde, Berge, Wahrzeichen, historische Schiffe, Whisky, Weine,
Swatch-Uhren), stehen auf `language: neutral`. Sie erscheinen in jeder Sprache
und übernehmen die Modifikatoren der gewählten - `Silent Secretariat` auf
Englisch, `Stiller Secretariat` auf Deutsch.

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

Tasten: `r` neu generieren · `c` Slug kopieren · `n` Name kopieren · `m` Mutation +25% · `t` Thema wechseln · `f` Favorit · `v` Favoriten anzeigen · `l` Sprache · `a` Info · `q` beenden

Das linke Einstellungspanel hat drei Schieberegler - **Mutationswahrscheinlichkeit**
(0-100%), **Wortanzahl** (1, 2 oder 3 sichtbare Wörter pro Name) und
**Vorschläge** (10/20/30/40 Namen pro Stapel) - dazu eine Auswahlliste für die
**Sprache** (siehe [Sprachen](#sprachen)). Das Verschieben eines Reglers
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
uv run codename --list-themes --lang de  # deutsche plus neutrale Themen
uv run codename -t tierwelt -n 10       # deutsche Namen, korrekt gebeugt
uv run codename -t swatch --lang de      # Eigennamen, deutsche Modifikatoren
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

## Sprachen

Ein Thema gibt seine Sprache an, und die Sprache entscheidet, aus welchen
Modifikator-Pools es zieht, wie der Name zusammengesetzt wird und ob der
Modifikator gebeugt wird. Themen ohne `language`-Schlüssel sind englisch. Ein
Thema aus Eigennamen bekommt `language: neutral` - es bleibt in jeder Sprache
sichtbar und borgt sich die Modifikatoren der gerade aktiven.

```yaml
name: Tierwelt
description: Heimische Tiere
language: de
words:
  - Falke|m
  - Eule|f
  - Wiesel|n
```

Der Marker `|m` / `|f` / `|n` / `|p` ist das Genus des Substantivs. Deutsch
beugt den vorangestellten Modifikator danach - aus `still` wird
`Stiller Falke`, `Stille Eule`, `Stilles Wiesel`. Ohne Marker gilt das
Maskulinum. Sprachen ohne Flexion (Englisch) ignorieren ihn.

Die Modifikator-Pools liegen je Sprache in
`src/codename_generator/data/modifiers/<lang>/` - `adjectives.yaml`,
`verbs.yaml` und `agents.yaml`. Eine Sprache ohne eigenen Ordner fällt auf die
englischen Pools zurück. Die deutschen Verben sind Partizipien I (`jagend`,
`lauernd`), weil das Deutsche genau die vor das Substantiv stellt.

Auch die Wortstellung unterscheidet sich: Deutsch stellt kein Partizip nach,
deshalb entfällt `theme-verb` ("Falke Jagend") und dreiteilige Namen nutzen
`adj-verb-theme` ("Stiller Jagender Falke") statt `adj-theme-verb`.

Jede Sprache bekommt ihr eigenes **Random**-Thema (`random`, `random-de`, ...),
damit ein gepoolter Zug nie ein deutsches Substantiv mit einem englischen
Adjektiv kombiniert - die neutralen Themen fließen in alle ein.

Die Sprache wählst du im Einstellungspanel (unterste Auswahlliste) oder
schaltest sie mit `l` weiter. Die Themenliste zeigt dann diese Sprache plus
die neutralen Themen, und jeder Name wird mit deren Modifikatoren erzeugt. Auf
der CLI macht `--lang` dasselbe, für `--list-themes` wie für die Generierung.
Die Einstellung wird wie die Schieberegler gespeichert. Slugs bleiben ASCII:
Umlaute werden ausgeschrieben (`Grüner Blitz -> gruener-blitz`), Akzente
fallen weg (`Volupté -> volupte`).

## Danksagung

Die Einstellungs-Schieberegler nutzen [textual-slider](https://github.com/TomJGooding/textual-slider)
von [Tom J Gooding](https://github.com/TomJGooding) - danke für das Widget.

## Lizenz

Apache License 2.0 - siehe [LICENSE](LICENSE).
