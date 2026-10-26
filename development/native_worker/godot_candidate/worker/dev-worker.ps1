[CmdletBinding()]
param([ValidateSet('Build','Result','Status','Start','Stop')][string]$Action='Status',[ValidatePattern('^[a-f0-9]{32}$')][string]$OperationId,[ValidateSet('build_studio_dev','build_godot_dev')][string]$Scenario='build_studio_dev')
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$tools=(Get-Content -LiteralPath (Join-Path $root 'TOOLS.json') -Raw | ConvertFrom-Json).paths
if ($Action -eq 'Start') { & (Join-Path $root 'autostart/manage-task.ps1') -Action Start;exit 0 }
if ($Action -eq 'Status' -or $Action -eq 'Stop') {
    $raw=& $tools.python -B -I (Join-Path $root 'host.py') $Action.ToLowerInvariant()
} else {
    if (-not $OperationId) { if ($Action -eq 'Result') { throw 'Result requires -OperationId' };$OperationId=[guid]::NewGuid().ToString('N') }
    $verb=if ($Action -eq 'Build') { 'submit' } else { 'status' }
    $request=@{action=$verb;operation_id=$OperationId;scenario=$Scenario} | ConvertTo-Json -Compress
    $raw=& $tools.python -B -I (Join-Path $root 'broker.py') --request $request
}
$exitCode=$LASTEXITCODE
$result=$raw | ConvertFrom-Json
$result | ConvertTo-Json -Depth 15
if ($exitCode -ne 0 -or $result.state -in @('DENIED','ERROR','HOLD','BUSY')) { throw "DEV worker $($result.state): $($result.reason); no automatic retry" }
