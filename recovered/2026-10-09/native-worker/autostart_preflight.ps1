$ErrorActionPreference='Stop'
$root='F:\Remaster Framework\orchestrator\native-worker'
$task='OpenRemaster-NativeWorker'
$action=New-ScheduledTaskAction -Execute "$root\runtime\python.exe" -Argument ('"'+$root+'\service_entry.py"') -WorkingDirectory $root
$trigger=New-ScheduledTaskTrigger -AtStartup
$settings=New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -MultipleInstances IgnoreNew
$principal=New-ScheduledTaskPrincipal -UserId 'HomePC\OpenRemasterWorker' -LogonType Password -RunLevel Limited
[pscustomobject]@{Task=$task;Execute=$action.Execute;Arguments=$action.Arguments;Trigger='AtStartup';Identity=$principal.UserId;LogonType=$principal.LogonType;Registered=[bool](Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue)}|ConvertTo-Json
