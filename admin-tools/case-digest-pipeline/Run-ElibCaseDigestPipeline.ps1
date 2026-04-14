# Unified E-Library case digest pipeline: fetch HTML, Markdown, Postgres INSERT, Gemini digest.
# Run from repo root (script cd's there). Pass through any CLI args, e.g. --ids 70193
#
#   .\admin-tools\case-digest-pipeline\Run-ElibCaseDigestPipeline.ps1
#   .\admin-tools\case-digest-pipeline\Run-ElibCaseDigestPipeline.ps1 --ids 70193
#
# Requires: DB_CONNECTION_STRING; GOOGLE_API_KEY when new rows are ingested.

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location -LiteralPath $RepoRoot
python (Join-Path $RepoRoot "scripts\elib_digest_pipeline.py") @args
exit $LASTEXITCODE
