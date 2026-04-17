$ErrorActionPreference = "Stop"

$gcloudCmd = "C:\Users\rnlar\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

Write-Host "Copying bundled Python..."
$pyPath = & $gcloudCmd components copy-bundled-python
Write-Host "Python path: $pyPath"

$env:CLOUDSDK_PYTHON = $pyPath

Write-Host "Installing alpha components..."
& $gcloudCmd components install alpha --quiet

Write-Host "Component installation complete. Checking billing accounts..."
& $gcloudCmd alpha billing accounts list
