#Requires -Version 5.1
<#
.SYNOPSIS
    Rendert eine VHS-Tape aus dem demo/-Verzeichnis.
.DESCRIPTION
    Aufruf:
        .\tape.ps1            -> listet verfuegbare Tapes
        .\tape.ps1 intro      -> rendert demo/intro.tape
        .\tape.ps1 intro.tape -> dito (Endung optional)
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

# Endung optional - normalisieren.
if (-not $name.EndsWith(".tape")) { $name = "$name.tape" }
$tapePath = Join-Path $demoDir $name

if (-not (Test-Path $tapePath)) {
    Write-Error "Tape nicht gefunden: $tapePath"
    exit 1
}

# Verifizieren dass vhs auf dem PATH liegt.
$vhsCmd = Get-Command vhs -ErrorAction SilentlyContinue
if (-not $vhsCmd) {
    Write-Error "vhs ist nicht installiert oder nicht im PATH. Siehe demo/README oder den vhs-Skill."
    exit 1
}

Write-Host "Rendering $name ..." -ForegroundColor Cyan
$started = Get-Date

& vhs $tapePath

if ($LASTEXITCODE -ne 0) {
    Write-Error "vhs-Lauf fehlgeschlagen (Exit $LASTEXITCODE)"
    exit $LASTEXITCODE
}

$elapsed = [int]((Get-Date) - $started).TotalSeconds
Write-Host "Fertig in ${elapsed}s" -ForegroundColor Green
