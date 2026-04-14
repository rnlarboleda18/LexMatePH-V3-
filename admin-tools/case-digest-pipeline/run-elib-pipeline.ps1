# Back-compat wrapper: delegates to Run-ElibCaseDigestPipeline.ps1
& "$PSScriptRoot\Run-ElibCaseDigestPipeline.ps1" @args
exit $LASTEXITCODE
