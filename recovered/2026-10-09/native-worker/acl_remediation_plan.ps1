$ErrorActionPreference='Stop'
$root='F:\Remaster Framework\orchestrator\native-worker'
$worker='HomePC\OpenRemasterWorker'
$plan=@(
 @{Path=$root;Role='CODE';Worker='RX';Action='REMOVE_INHERITED_MODIFY_AFTER_BACKUP'},
 @{Path=(Join-Path $root 'queue');Role='QUEUE';Worker='M';Action='EXPLICIT_WORKER_MODIFY'},
 @{Path='F:\Remaster Framework\orchestrator\control-plane';Role='CODE';Worker='RX';Action='REMOVE_INHERITED_MODIFY_AFTER_BACKUP'},
 @{Path='F:\Remaster Framework\runtime-test\results';Role='EVIDENCE';Worker='M';Action='ISOLATE_PER_JOB_AFTER_BACKUP'},
 @{Path='F:\Remaster Framework\source';Role='CORPUS';Worker='RX';Action='KEEP_UNCHANGED'}
)
$plan|ConvertTo-Json -Depth 4
