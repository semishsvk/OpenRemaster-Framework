param([Parameter(Mandatory=$true)][string]$Job)
$ErrorActionPreference='Stop'
$j=Get-Content -Raw $Job|ConvertFrom-Json; $cfg=Get-Content -Raw "$PSScriptRoot\config\worker.json"|ConvertFrom-Json
$project=[string]$j.project_path; $pg=Join-Path $project 'project.godot'
if($j.schema -ne 'GodotRuntimeJob.v1'){throw 'Unsupported job schema'}; if(!(Test-Path $pg)){throw "project.godot missing: $pg"}
$out=Join-Path $cfg.runtime_root ("results\"+$j.job_id); New-Item -ItemType Directory -Force -Path $out|Out-Null
$stdout=Join-Path $out 'stdout.log'; $stderr=Join-Path $out 'stderr.log'; $start=(Get-Date).ToUniversalTime(); $sw=[Diagnostics.Stopwatch]::StartNew()
$args=@('--path',$project); if(@('smoke','headless','replay','import') -contains $j.mode){$args+='--headless'}; if($j.mode -eq 'import'){$args+=@('--editor','--quit')}; if($j.args){$args+=@($j.args)}
& $cfg.godot_console @args 1>$stdout 2>$stderr; $exitCode=$LASTEXITCODE; $sw.Stop()
$expected=if($null -ne $j.expected_exit_code){[int]$j.expected_exit_code}else{0}; $status=if($exitCode -eq $expected){'PASS'}else{'FAIL'}
$fp=[ordered]@{schema='ExecutionEnvironmentFingerprint.v1';captured_at=(Get-Date).ToUniversalTime().ToString('o');machine=[Environment]::MachineName;os=[Environment]::OSVersion.VersionString;godot_version=$cfg.expected_version;godot_sha256=(Get-FileHash $cfg.godot_console -Algorithm SHA256).Hash;project_godot_sha256=(Get-FileHash $pg -Algorithm SHA256).Hash;capture_authority=$cfg.capture_authority;remote_desktop_capture_authority=$false}
$result=[ordered]@{schema='GodotRuntimeResult.v1';job_id=$j.job_id;project=$j.project;mode=$j.mode;status=$status;exit_code=$exitCode;expected_exit_code=$expected;started_at=$start.ToString('o');finished_at=(Get-Date).ToUniversalTime().ToString('o');duration_seconds=[math]::Round($sw.Elapsed.TotalSeconds,3);fingerprint=$fp;stdout_sha256=(Get-FileHash $stdout -Algorithm SHA256).Hash;stderr_sha256=(Get-FileHash $stderr -Algorithm SHA256).Hash}
$result|ConvertTo-Json -Depth 8|Set-Content -Encoding UTF8 (Join-Path $out 'result.json'); $fp|ConvertTo-Json -Depth 8|Set-Content -Encoding UTF8 (Join-Path $out 'fingerprint.json'); $result|ConvertTo-Json -Depth 8
if($status -ne 'PASS'){exit 1}
