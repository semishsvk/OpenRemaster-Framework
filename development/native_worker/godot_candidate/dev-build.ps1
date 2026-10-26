<#
Canonical unsigned DEV build control. Default: live worker status.
Build: enqueue build_studio_dev. Result: read the existing operation, never rebuild.
Current profile builds the pinned Studio snapshot; no production certificate required.
#>
[CmdletBinding()]
param([ValidateSet('Build','Result','Status','Start','Stop')][string]$Action='Status',[ValidatePattern('^[a-f0-9]{32}$')][string]$OperationId,[ValidateSet('build_studio_dev','build_godot_dev')][string]$Scenario='build_studio_dev')
$ErrorActionPreference='Stop'
$active=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'ACTIVE-WORKER.json') -Raw | ConvertFrom-Json
if ($active.profile -ne 'DEV_UNSIGNED' -or $active.production_go -ne $false) { throw 'Explicit DEV_UNSIGNED profile required' }
$client=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot $active.client))
$prefix=[IO.Path]::GetFullPath($PSScriptRoot)+[IO.Path]::DirectorySeparatorChar
if (-not $client.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Client must stay in this workspace' }
if ((Get-FileHash -LiteralPath $client -Algorithm SHA256).Hash.ToLowerInvariant() -ne $active.client_sha256) { throw 'Active client source changed' }
if ($OperationId -and $Action -in @('Status','Start','Stop')) { throw 'OperationId is only for Build or Result' }
$parameters=@{Action=$Action;Scenario=$Scenario}
if ($OperationId) { $parameters.OperationId=$OperationId }
& $client @parameters
