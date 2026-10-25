$ErrorActionPreference='Stop'
$root='F:\Remaster Framework\orchestrator\native-worker'
$python=(Get-Command python).Source
$task='OpenRemaster-NativeWorker'
$action=New-ScheduledTaskAction -Execute $python -Argument ('"'+$root+'\agent.py"') -WorkingDirectory $root
$trigger=New-ScheduledTaskTrigger -AtStartup
$settings=New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Seconds 0)
Write-Output "PREPARED_ONLY: $task; python=$python; startup trigger; no registration"
