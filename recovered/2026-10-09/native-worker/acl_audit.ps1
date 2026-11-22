$ErrorActionPreference='Stop'
$root='F:\Remaster Framework\orchestrator\native-worker'
$identity='HomePC\OpenRemasterWorker'
$paths=@($root,(Join-Path $root 'queue'),'F:\Remaster Framework\orchestrator\control-plane','F:\Remaster Framework\source','F:\Remaster Framework\runtime-test\results')
$report=foreach($p in $paths){
 $acl=Get-Acl -LiteralPath $p
 [pscustomobject]@{path=$p;owner=$acl.Owner;protected=$acl.AreAccessRulesProtected;worker_explicit=@($acl.Access|Where-Object {$_.IdentityReference.Value -ieq $identity -and -not $_.IsInherited}|ForEach-Object {$_.FileSystemRights.ToString()});authenticated_modify=@($acl.Access|Where-Object {$_.IdentityReference.Value -match 'Authenticated Users' -and $_.FileSystemRights.ToString() -match 'Modify'}).Count -gt 0}
}
$report|ConvertTo-Json -Depth 4
