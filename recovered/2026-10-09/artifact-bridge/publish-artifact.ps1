param([Parameter(Mandatory=$true)][string]$File,[Parameter(Mandatory=$true)][string]$Project,[string]$Kind='artifact',[string]$Classification='UNVERIFIED')
$ErrorActionPreference='Stop'
$j = python "$PSScriptRoot\publish_artifact.py" $File --project $Project --kind $Kind --classification $Classification | ConvertFrom-Json
if (-not $j.sha256) { throw 'Artifact publish failed' }
$latest = Join-Path $PSScriptRoot "manifests\latest-$Project-$Kind.json"
$j | ConvertTo-Json -Depth 8 | Set-Content -Encoding ascii $latest
Write-Output ($j | ConvertTo-Json -Compress)