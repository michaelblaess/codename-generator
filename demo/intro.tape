# codename-generator intro
#
# Rendert ein ca. 25-Sekunden GIF, das die Kernfeatures zeigt:
#   1. App-Start mit Themes-Liste
#   2. Custom Seed "Sitemap" eingeben -> 30 Vorschlaege
#   3. Regenerate fuer andere Modifier-Kombination
#   4. Zweiter Seed "Inspector" zum Vergleich
#   5. Einen Favoriten markieren
#
# Aufruf aus dem Repo-Root:
#   .\tape.ps1 intro
#   bzw. direkt:
#   vhs demo\intro.tape

Output demo/intro.gif

Require uv

# ---------- Set ----------
Set Shell "pwsh"
Set FontSize 14
Set Width 1400
Set Height 900
Set Padding 20
Set Margin 20
Set MarginFill "#1e1e2e"
Set BorderRadius 8
Set WindowBar Colorful
Set WindowBarSize 40
Set Theme "Catppuccin Mocha"
Set TypingSpeed 80ms
Set FrameRate 60
Set LoopOffset 5%
Set CursorBlink false

# ---------- Setup (unsichtbar) ----------
Hide
# UTF-8 erzwingen - sonst zerlegt es die Umlaute / Sonderzeichen.
Type "$OutputEncoding = [System.Text.Encoding]::UTF8"
Enter
Type "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8"
Enter
Type "cls"
Enter
Type "uv run codename"
Enter
# Warten bis die TUI sicher steht (Sidebar zeigt "Custom Seed").
Wait /Custom Seed/
Sleep 400ms
Show

# ---------- Demo ----------

# 1) Initialer Zustand kurz wirken lassen.
Sleep 1500ms

# 2) Custom Seed "Sitemap" eingeben.
Type@180ms "i"
Wait /Your idea/
Sleep 400ms
# Eingabefeld kann mit altem Seed vorbefuellt sein - grosszuegig leeren.
Backspace 30
Type "Sitemap"
Sleep 500ms
Enter
Wait /seed: Sitemap/
Sleep 2200ms

# 3) Regenerate fuer eine andere Modifier-Kombination.
Type "r"
Sleep 2500ms

# 4) Anderer Seed "Inspector" zum Vergleich.
Type@180ms "i"
Wait /Your idea/
Sleep 400ms
Backspace 30
Type "Inspector"
Sleep 500ms
Enter
Wait /seed: Inspector/
Sleep 2500ms

# 5) Einen Favoriten markieren (auf der ersten Zeile).
Type "f"
Sleep 1500ms

# Endbild stabil halten - sieht im GIF-Loop besser aus.
Sleep 1000ms

# ---------- Cleanup (unsichtbar) ----------
Hide
Type "q"
Sleep 300ms
