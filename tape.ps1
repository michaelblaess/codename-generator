#Requires -Version 5.1
<#
.SYNOPSIS
    Rendert eine VHS-Tape aus dem demo/-Verzeichnis via WSL.
.DESCRIPTION
    Aufruf:
        .\tape.ps1            -> listet verfuegbare Tapes
        .\tape.ps1 intro      -> rendert demo/intro.tape
        .\tape.ps1 intro.tape -> dito (Endung optional)

    Verwendet WSL Ubuntu - VHS hat unter Windows nativ einen bekannten
    Hang-Bug (Issue #721). Setup einmalig per demo/install-wsl.sh.
#>
$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$demoDir = Join-Path $root "demo"

if (-not (Test-Path $demoDir)) {
    Write-Error "demo/-Verzeichnis fehlt: $demoDir"
    exit 1
}

$name = $args[0]
if (-not $name) {
    Write-Host "Verfuegbare Tapes:" -ForegroundColor Cyan
    Get-ChildItem $demoDir -Filter "*.tape" | ForEach-Object {
        Write-Host "  $($_.BaseName)" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "Aufruf: .\tape.ps1 <name>" -ForegroundColor Gray
    exit 0
}

if (-not $name.EndsWith(".tape")) { $name = "$name.tape" }
$tapePath = Join-Path $demoDir $name

if (-not (Test-Path $tapePath)) {
    Write-Error "Tape nicht gefunden: $tapePath"
    exit 1
}

$wslCmd = Get-Command wsl -ErrorAction SilentlyContinue
if (-not $wslCmd) {
    Write-Error "wsl ist nicht verfuegbar. WSL muss installiert sein."
    exit 1
}

Write-Host "Rendering $name in WSL Ubuntu ..." -ForegroundColor Cyan
$started = Get-Date

# WSL-Pfad zur Repo-Root und Tape-Datei.
$wslRoot = "/mnt/c/Users/Michael/Repos/codename-generator"
$wslTape = "demo/$name"

# In WSL: ins Repo-Verzeichnis wechseln, dann vhs ausfuehren.
# PATH so erweitern dass uv (~/.local/bin) gefunden wird.
& wsl -d Ubuntu-22.04 -- bash -c "export PATH=`$HOME/.local/bin:`$PATH; cd $wslRoot && vhs $wslTape"

if ($LASTEXITCODE -ne 0) {
    Write-Error "vhs-Lauf fehlgeschlagen (Exit $LASTEXITCODE). Setup OK? Siehe demo/install-wsl.sh"
    exit $LASTEXITCODE
}

$elapsed = [int]((Get-Date) - $started).TotalSeconds
Write-Host "Fertig in ${elapsed}s" -ForegroundColor Green
$outputGif = Join-Path $demoDir ([System.IO.Path]::GetFileNameWithoutExtension($name) + ".gif")
if (Test-Path $outputGif) {
    $size = [math]::Round((Get-Item $outputGif).Length / 1KB, 1)
    Write-Host "  -> $outputGif ($size KB)" -ForegroundColor Gray
}
