$ErrorActionPreference='Stop'
$root='F:\Remaster Framework\orchestrator\native-worker'
$py=Join-Path $root 'runtime\python.exe'
$probe=Join-Path $root 'identity_probe.py'
$report=[ordered]@{
 worker_account='HomePC\OpenRemasterWorker'
 task_scheduler_running=((Get-Service Schedule).Status -eq 'Running')
 python_exists=(Test-Path $py)
 python_probe_exists=(Test-Path $probe)
 task_registration_requires_admin_or_credentialed_setup=$true
 service_registration_pending=$true
 transport_pending=$true
 no_reboot=$true
}
$report|ConvertTo-Json
