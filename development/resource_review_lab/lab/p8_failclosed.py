"""Isolated outer fail-closed adapter, no production privileges."""
import hashlib
DISABLED_FLAGS=('may_enqueue','may_dispatch','may_start_worker','may_sign','may_publish','may_promote','may_fallback','automatic_retry','production_authority','dispatch_authorized','worker_execution_authorized','independent_authority_verified','release_eligible','production_go')
def disabled():return {flag:False for flag in DISABLED_FLAGS}
def observe_safely(provider,now=None):
 try:
  result=provider.observe(now)
  if type(result) is not dict:raise ValueError("INVALID_RESULT")
  if len(result)>64 or any(type(key) is not str or key.startswith('may_') and key not in DISABLED_FLAGS for key in result):raise ValueError('UNKNOWN_OR_UNBOUNDED_CAPABILITY_FIELD')
  if result.get("may_dispatch") is not False or result.get("may_start_worker") is not False:raise ValueError("UNTRUSTED_AUTHORITY")
  if any(flag in result and result[flag] is not False for flag in DISABLED_FLAGS):raise ValueError('UNTRUSTED_CAPABILITY_CLAIM')
  if result.get("status") not in ("HOLD_NO_AUTO_RETRY","READONLY_OBSERVATION_VALIDATED_NOT_AUTHORITY"):raise ValueError("UNKNOWN_STATUS")
  return {**result,**disabled()}
 except Exception as exc:
  return {"status":"HOLD_NO_AUTO_RETRY","reason_code":"UNEXPECTED_PROVIDER_FAILURE","error_type":type(exc).__name__,**disabled()}

JOURNAL_HOLDS=frozenset(('INPUT_SCHEMA_HOLD','WINDOWS_LOCK_UNAVAILABLE_HOLD','JOURNAL_IO_HOLD','LOCK_TIMEOUT_HOLD','PARTIAL_JOURNAL_HOLD','JOURNAL_JSON_OR_SCHEMA_HOLD','JOURNAL_EVENT_SCHEMA_HOLD','HASH_CHAIN_HOLD','JOURNAL_HISTORY_REPLAY_HOLD','JOURNAL_BOUND_HOLD'))
def observe_journal_status(status,now=None):
 """Map an already reported status only; never call journal, queue or query."""
 class Reported:
  def observe(self,unused):
   reason='UNRECOGNIZED_JOURNAL_STATUS';query_only=False
   if type(status) is str and len(status)<=128:
    if status in JOURNAL_HOLDS:reason=status
    elif status=='SHADOW_RESERVED':reason='SHADOW_RESERVATION_NOT_AUTHORITY'
    elif status=='REPLAY_REJECTED':reason='JOURNAL_REPLAY_QUERY_ONLY';query_only=True
    elif status=='JOURNAL_WRITE_UNCERTAIN_HOLD':reason='JOURNAL_WRITE_UNCERTAIN_QUERY_ONLY';query_only=True
   return dict(status='HOLD_NO_AUTO_RETRY',reason_code=reason,query_only=query_only,query_performed=False,scope='REPORTED_SHADOW_JOURNAL_STATUS_NOT_ADMISSION',**disabled())
 return observe_safely(Reported(),now)
