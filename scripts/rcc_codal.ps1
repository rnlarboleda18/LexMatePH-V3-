# RCC codal CLI wrapper (repo root). Usage:
#   .\scripts\rcc_codal.ps1 --help
#   .\scripts\rcc_codal.ps1 all --raw LexCode\Codals\md\RCC_raw.md --clear --verify
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
& python (Join-Path $PSScriptRoot "rcc_codal_cli.py") @args
exit $LASTEXITCODE
