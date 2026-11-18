param(
    [Parameter(Mandatory = $true)][string]$Commit,
    [Parameter(Mandatory = $true)][string]$RunUrl,
    [string]$OutputDirectory = 'windows-dev-output'
)

$ErrorActionPreference = 'Stop'
if ($Commit -notmatch '^[a-f0-9]{40}$') { throw 'A full source commit is required.' }
$studio = Split-Path $PSScriptRoot -Parent
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
}
$info | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $package 'BUILD-INFO.json') -Encoding utf8
$sums = Get-ChildItem -LiteralPath $package -File | Sort-Object Name | ForEach-Object { '{0}  {1}' -f (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant(), $_.Name }
$sums | Set-Content -LiteralPath (Join-Path $package 'SHA256SUMS.txt') -Encoding ascii
$archive = Join-Path $output "OpenRemaster-Studio-DEV-windows-x64-$($Commit.Substring(0, 12)).zip"
Compress-Archive -LiteralPath $package -DestinationPath $archive
'{0}  {1}' -f (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash.ToLowerInvariant(), (Split-Path $archive -Leaf) | Set-Content -LiteralPath "$archive.sha256" -Encoding ascii
Write-Output $archive
