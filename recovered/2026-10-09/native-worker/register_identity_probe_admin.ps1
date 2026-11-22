$ErrorActionPreference='Stop'
$root='F:\Remaster Framework\orchestrator\native-worker'
$py=Join-Path $root 'runtime\python.exe'
$probe=Join-Path $root 'identity_probe.py'
$task='OpenRemaster-IdentityProbe'
$action=New-ScheduledTaskAction -Execute $py -Argument ('"'+$probe+'"') -WorkingDirectory $root
$principal=New-ScheduledTaskPrincipal -UserId 'HomePC\OpenRemasterWorker' -LogonType S4U -RunLevel Limited
if(Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue){throw 'TASK_ALREADY_EXISTS'}
Register-ScheduledTask -TaskName $task -Action $action -Principal $principal -Description 'One-time non-destructive identity probe; remove after validation' -ErrorAction Stop | Out-Null
Write-Output 'REGISTERED_IDENTITY_PROBE_ONLY; no startup trigger; no reboot'
