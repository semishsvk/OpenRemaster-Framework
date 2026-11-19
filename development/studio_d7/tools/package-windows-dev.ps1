param(
    [Parameter(Mandatory = $true)][string]$Commit,
    [Parameter(Mandatory = $true)][string]$RunUrl,
    [string]$OutputDirectory = 'windows-dev-output'
)

$ErrorActionPreference = 'Stop'
if ($Commit -notmatch '^[a-f0-9]{40}$') { throw 'A full source commit is required.' }
$studio = Split-Path $PSScriptRoot -Parent
$reviewText = & python -B (Join-Path $PSScriptRoot 'verify_controls_review.py') --studio $studio --commit $Commit
if ($LASTEXITCODE -ne 0) { throw 'README_HOLD: exact source controls review required.' }
$controlsReview = $reviewText | ConvertFrom-Json
$output = [IO.Path]::GetFullPath((Join-Path $studio $OutputDirectory))
if (Test-Path -LiteralPath $output) { throw 'Use a fresh output directory.' }
$package = Join-Path $output 'OpenRemaster-Studio-DEV'
New-Item -ItemType Directory -Path $package -Force | Out-Null
$executable = Join-Path $studio 'src-tauri/target/release/openremaster_studio_shadow.exe'
$binary = Join-Path $package 'OpenRemaster-Studio-DEV.exe'
Copy-Item -LiteralPath $executable -Destination $binary
Copy-Item -LiteralPath (Join-Path $studio 'WINDOWS-DEV.txt') -Destination (Join-Path $package 'README.txt')
Copy-Item -LiteralPath (Join-Path $studio 'LICENSING-PROPOSAL.txt') -Destination $package

$metadataText = & cargo metadata --manifest-path (Join-Path $studio 'src-tauri/Cargo.toml') --locked --features custom-protocol --format-version 1 --filter-platform x86_64-pc-windows-msvc
if ($LASTEXITCODE -ne 0) { throw 'Cargo metadata failed.' }
$metadata = ($metadataText -join "`n") | ConvertFrom-Json
$resolved = @($metadata.resolve.nodes.id)
$inventory = [Collections.Generic.List[object]]::new()
$notices = [Text.StringBuilder]::new()
[void]$notices.AppendLine('Dependency notices collected for this DEV build')
foreach ($dependency in $metadata.packages | Sort-Object name, version) {
    if ($dependency.id -notin $resolved -or $dependency.source -notlike 'registry+*') { continue }
    $directory = Split-Path $dependency.manifest_path -Parent
    $files = @(Get-ChildItem -LiteralPath $directory -File | Where-Object Name -Match '^(LICENSE|LICENCE|COPYING|NOTICE|UNLICENSE|COPYRIGHT)([._-]|$)')
    if ($dependency.license_file) {
        $declared = Join-Path $directory $dependency.license_file
        if (Test-Path -LiteralPath $declared) { $files += Get-Item -LiteralPath $declared }
    }
    $files = @($files | Sort-Object FullName -Unique)
    $inventory.Add([ordered]@{ ecosystem = 'cargo'; name = $dependency.name; version = $dependency.version; license = $dependency.license; repository = $dependency.repository; notice_files = @($files.Name) })
    [void]$notices.AppendLine("`n$($dependency.name) $($dependency.version) — $($dependency.license)")
    foreach ($file in $files) {
        [void]$notices.AppendLine($file.Name)
        [void]$notices.AppendLine((Get-Content -Raw -LiteralPath $file.FullName))
    }
    if ($files.Count -eq 0) { [void]$notices.AppendLine('Notice text requires review against the declared license.') }
}
$nodePaths = & npm ls --omit=dev --all --parseable
if ($LASTEXITCODE -ne 0) { throw 'Node dependency inventory failed.' }
foreach ($directory in $nodePaths | Select-Object -Skip 1) {
    $dependency = Get-Content -Raw -LiteralPath (Join-Path $directory 'package.json') | ConvertFrom-Json
    $files = @(Get-ChildItem -LiteralPath $directory -File | Where-Object Name -Match '^(LICENSE|LICENCE|COPYING|NOTICE|UNLICENSE|COPYRIGHT)([._-]|$)')
    $inventory.Add([ordered]@{ ecosystem = 'npm'; name = $dependency.name; version = $dependency.version; license = $dependency.license; notice_files = @($files.Name) })
    [void]$notices.AppendLine("`n$($dependency.name) $($dependency.version) — $($dependency.license)")
    foreach ($file in $files) { [void]$notices.AppendLine((Get-Content -Raw -LiteralPath $file.FullName)) }
    if ($files.Count -eq 0) { [void]$notices.AppendLine('Notice text requires review against the declared license.') }
}
$inventory | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $package 'dependency-inventory.json') -Encoding utf8
$notices.ToString() | Set-Content -LiteralPath (Join-Path $package 'THIRD-PARTY-NOTICES.txt') -Encoding utf8
$configuration = Get-Content -Raw -LiteralPath (Join-Path $studio 'src-tauri/tauri.conf.json') | ConvertFrom-Json
$signature = Get-AuthenticodeSignature -LiteralPath $binary
if ($signature.Status -ne 'NotSigned') { throw 'Expected an unsigned DEV executable.' }
$info = [ordered]@{
    product = $configuration.productName
    version = $configuration.version
    source_commit = $Commit
    built_at_utc = [DateTime]::UtcNow.ToString('o')
    run_url = $RunUrl
    target = 'x86_64-pc-windows-msvc'
    features = @('custom-protocol')
    rustc = (& rustc --version)
    node = (& node --version)
    executable_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $binary).Hash.ToLowerInvariant()
    authenticode = [string]$signature.Status
    dependency_notice_gaps = @($inventory | Where-Object { $_.notice_files.Count -eq 0 } | ForEach-Object { "$($_.ecosystem)/$($_.name)@$($_.version)" })
    production_go = $false
    signing_provider = 'PENDING'
    proposed_license = 'MIT_PENDING_OWNER_APPROVAL'
    controls_review = $controlsReview
}
$info | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $package 'BUILD-INFO.json') -Encoding utf8
$buildId="studio-dev-$Commit"
$date=([DateTime]::Parse($info.built_at_utc)).ToString('yyyy-MM-dd')
$readme=@"
# OpenRemaster Studio Windows DEV

**Project:** OpenRemasterStudio
**Build ID:** $buildId
**Build date:** $date
**Platform:** Windows x64, WebView2
**Launcher:** OpenRemaster-Studio-DEV.exe
**Verification status:** VERIFIED
**Reviewed by:** $($controlsReview.reviewer)
**Reviewed at:** $($controlsReview.reviewed_at)
**Verification method:** Source-controls review record $($controlsReview.record_sha256); source census and SHA-256 values checked against this Git checkout. Runtime checks are separate.
**Source/InputMap evidence:** Git $Commit; reviewed source fingerprint $($controlsReview.source_fingerprint); controls-review.json records every covered source file
**Runtime test evidence:** Native startup at $RunUrl; separate Chromium review scenarios use mocked worker IPC and do not prove a HomePC build

## Launch instructions
Extract this package and open OpenRemaster-Studio-DEV.exe. Microsoft Edge WebView2 Runtime must already be installed. This is an unsigned DEV preview. Source commit: $Commit. Executable SHA-256: $($info.executable_sha256).

## Movement / navigation
| Device | Control | Action | Evidence |
| --- | --- | --- | --- |
| Mouse | Click navigation or use the wheel | Open Studio pages and scroll | App.tsx; browser route checks |
| Keyboard | Ctrl+K | Focus page search | QuickNavigation.tsx; browser shortcut check |
| Keyboard | Up / Down, Enter, Escape in page search | Select a matching page or clear search | quicknav-logic.ts; source control review |
| Keyboard | Tab / Shift+Tab | Move between standard controls | Native HTML controls; browser focus check |

## Interaction / gameplay
Not implemented in this build: original-game playback, movement and gamepad interaction are absent from this Studio UI. Evidence: App.tsx and the registered native commands.

## Menus / inventory / save-load
| Device | Control | Action | Evidence |
| --- | --- | --- | --- |
| Mouse / keyboard | Settings and Build Lab controls | Inspect build identity, releases, diagnostics and saved operation status | StudioBuildIdentity.tsx; DevWorkerPanel.tsx; browser scenarios |
| Mouse / keyboard | Resolution note and explicit checkbox | Acknowledge a diagnosed hold while retaining its evidence | DevWorkerPanel.tsx; client behavioral tests |
Game inventory and save/load are not applicable. Studio stores operation metadata locally; reopening restores status checks without resubmitting.

## Graphics / display / camera
Not implemented in this build: classic/modern rendering switches, game camera, application fullscreen toggle and resolution selector are absent. Evidence: App.tsx; this is a resizable desktop UI with responsive browser layouts.

## Text / language / subtitles
Not implemented in this build: language, translation and subtitle switches are absent. The Studio shell is English. Evidence: index.html, App.tsx and English-source regression tests.

## Debug / diagnostics / QA
| Device | Control | Action | Evidence |
| --- | --- | --- | --- |
| Mouse / keyboard | Refresh diagnostics | Recheck the native DEV diagnostic view | DevWorkerPanel.tsx; dev_preflight.rs |
| Mouse / keyboard | Load log, source/file selectors, Previous/Next page | Inspect full logs by page | DevLogViewer.tsx; Python and browser scenarios |
| Mouse / keyboard | Search this page, Log level | Filter the displayed page | dev-diagnostics.ts; frontend tests |
| Mouse / keyboard | Follow live output | Refresh the live tail every ten seconds | DevLogViewer.tsx |
| Mouse / keyboard | Export complete diagnostic ZIP | Save a verified retained manifest and compressed logs | studio_dev_control.py; ZIP and browser tests |
Worker controls require a commissioned worker-enabled build. This public package contains the portable UI. No game cheats, debug console or screenshot hotkey is implemented.

## Other shortcuts
Not implemented in this build: additional application-specific function-key, controller or game shortcuts are absent. Evidence: QuickNavigation.tsx defines the page-search shortcut; other panels use standard HTML controls.

## Known limitations and unavailable features
Current Owner/Resource/GAME and Windows-role admission is not connected to the pinned worker 06 route. Native submission stays blocked. The original R07S2 source and this Git build require explicit reconciliation. Browser worker IPC is mocked in tests. Production admission, signing, final license/rights review and SignPath acceptance remain pending. This README verifies documented source controls; it does not certify original gameplay or production authority. See README.txt and BUILD-INFO.json for prerequisites, privacy and provenance.

## Verification
Build-specific source and checks: $RunUrl. Package source: $Commit. Complete package hashes: SHA256SUMS.txt. A successful technical build does not accept an Owner/Witness grant or authorize production activation.
The README verification label covers the documented source controls. Its reviewer and date come from a source-bound review record, not from the build clock. Source hashes normalize text CRLF to LF and preserve binary bytes. Changed or additional source files block packaging until a new review record is supplied. This record is not an independent signature or production release acceptance.
"@
$readme | Set-Content -LiteralPath (Join-Path $package 'README.md') -Encoding utf8
& python -B (Join-Path $PSScriptRoot 'verify_dev_build_readme.py') --build-dir $package --project OpenRemasterStudio --build-id $buildId
if ($LASTEXITCODE -ne 0) { throw 'Build-specific README gate failed.' }
$sums = Get-ChildItem -LiteralPath $package -File | Sort-Object Name | ForEach-Object { '{0}  {1}' -f (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant(), $_.Name }
$sums | Set-Content -LiteralPath (Join-Path $package 'SHA256SUMS.txt') -Encoding ascii
$archive = Join-Path $output "OpenRemaster-Studio-DEV-windows-x64-$($Commit.Substring(0, 12)).zip"
Compress-Archive -LiteralPath $package -DestinationPath $archive
'{0}  {1}' -f (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash.ToLowerInvariant(), (Split-Path $archive -Leaf) | Set-Content -LiteralPath "$archive.sha256" -Encoding ascii
Write-Output $archive
