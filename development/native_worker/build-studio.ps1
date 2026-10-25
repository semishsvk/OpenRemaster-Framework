[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidatePattern('^[a-f0-9]{32}$')][string]$OperationId)
$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$false
$root=$PSScriptRoot
$tools=(Get-Content -LiteralPath (Join-Path $root 'TOOLS.json') -Raw | ConvertFrom-Json).paths
$stage=Join-Path $root ('state/operations/'+$OperationId)
$studio=Join-Path $stage 'source/studio'
function Progress-Phase([string]$phase) {
    $progressPath=Join-Path $stage 'build-progress.json'
    $progressTemp=$progressPath+'.'+[guid]::NewGuid().ToString('N')+'.tmp'
    @{operation_id=$OperationId;phase=$phase;utc=[DateTimeOffset]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $progressTemp -Encoding utf8
    [IO.File]::Move($progressTemp,$progressPath,$true)
    Write-Output ('BUILD_PHASE='+$phase)
}
$env:CARGO_HOME=Join-Path $root 'cache/cargo'
$env:CARGO_TARGET_DIR=Join-Path $stage 'target'
$env:CARGO_NET_OFFLINE='true'
$env:CARGO_BUILD_JOBS='2'
$env:CARGO_INCREMENTAL='0'
$env:CARGO_PROFILE_DEV_DEBUG='0'
$env:CARGO_PROFILE_TEST_DEBUG='0'
$env:CARGO_CACHE_AUTO_CLEAN_FREQUENCY='never'
$env:RUSTC=$tools.rustc
$env:RUSTDOC=$tools.rustdoc
$env:PATH=(Split-Path $tools.cargo -Parent)+';C:\Program Files\nodejs;'+$env:PATH
foreach ($name in @('RUSTFLAGS','CARGO_ENCODED_RUSTFLAGS','RUSTC_WRAPPER','RUSTC_WORKSPACE_WRAPPER','TAURI_CONFIG','NODE_OPTIONS','CL','_CL_','LINK','_LINK_')) { [Environment]::SetEnvironmentVariable($name,$null,'Process') }
$env:TAURI_CONFIG='{}'
Push-Location $studio
try {
    Progress-Phase 'frontend-typecheck'
    & $tools.node (Join-Path $studio 'node_modules/typescript/bin/tsc') --noEmit
    if ($LASTEXITCODE -ne 0) { throw "Frontend typecheck exit $LASTEXITCODE" }
    Progress-Phase 'frontend-build'
    & $tools.node (Join-Path $studio 'node_modules/vite/bin/vite.js') build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build exit $LASTEXITCODE" }
    $cmdPath=Join-Path $stage 'native-build.cmd'
    $lines=@('@echo off','setlocal EnableExtensions DisableDelayedExpansion',('call "'+$tools.vcvars+'" > NUL'),'if errorlevel 1 exit /b 70',('cd /d "'+(Join-Path $studio 'src-tauri')+'"'),'if errorlevel 1 exit /b 71',('"'+$tools.cargo+'" build --locked --offline --features custom-protocol,dev-worker --jobs 2'),'if errorlevel 1 exit /b %errorlevel%',('"'+$tools.cargo+'" test --locked --offline --features custom-protocol,dev-worker --jobs 2'),'if errorlevel 1 exit /b %errorlevel%',('"'+$tools.cargo+'" test --locked --offline --features custom-protocol,dev-worker --jobs 2 dev_worker::tests::runtime_smoke_returns_dev_scope -- --ignored --exact --nocapture'),'exit /b %errorlevel%')
    $lines | Set-Content -LiteralPath $cmdPath -Encoding ascii
    Progress-Phase 'native-build-and-ipc-tests'
    & 'C:\Windows\System32\cmd.exe' /d /c $cmdPath
    if ($LASTEXITCODE -ne 0) { throw "Native build or IPC tests exit $LASTEXITCODE" }
    Progress-Phase 'artifact-validation'
    $binary=Join-Path $stage 'target/debug/openremaster_studio_shadow.exe'
    if (-not (Test-Path -LiteralPath $binary -PathType Leaf)) { throw 'Expected Studio EXE missing' }
    if (-not (Test-Path -LiteralPath (Join-Path $studio 'dist/index.html'))) { throw 'Frontend output missing' }
    $signature=Get-AuthenticodeSignature -LiteralPath $binary
    if ($signature.Status -ne 'NotSigned') { throw 'DEV_UNSIGNED expected an unsigned Studio EXE' }
    @{schema='OpenRemaster.DevBuildArtifacts.v1';profile='DEV_UNSIGNED';operation_id=$OperationId;studio_exe=$binary;studio_exe_sha256=(Get-FileHash -LiteralPath $binary -Algorithm SHA256).Hash.ToLowerInvariant();studio_exe_bytes=(Get-Item -LiteralPath $binary).Length;signature_status=[string]$signature.Status;frontend_index=(Join-Path $studio 'dist/index.html');frontend_index_sha256=(Get-FileHash -LiteralPath (Join-Path $studio 'dist/index.html') -Algorithm SHA256).Hash.ToLowerInvariant();frontend_build=$true;native_build=$true;native_ipc_tests=$true;gui_executed=$false;certificate_created=$false;installer_built=$false;production_go=$false} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $stage 'artifacts.json') -Encoding utf8
    Progress-Phase 'completed'
} finally { Pop-Location }
