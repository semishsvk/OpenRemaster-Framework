"""Isolated Windows cross-process locked journal. Test-only, no queue or authority."""
import pathlib,json,os,hashlib,time,re
try:
 import msvcrt
except ImportError:
 msvcrt=None  # No substitute lock; runtime admission stays HOLD off Windows.
MAX_BYTES=1024*1024
MAX_RECORDS=4096
class JournalInvalid(ValueError):pass
def valid_id(value):return type(value) is str and re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',value) is not None
def valid_hash(value):return type(value) is str and re.fullmatch(r'[0-9a-f]{64}',value) is not None
def validate_journal(raw):
 if type(raw) is not bytes or len(raw)>MAX_BYTES:raise JournalInvalid('JOURNAL_BOUND_HOLD')
 if raw and not raw.endswith(b'\n'):raise JournalInvalid('PARTIAL_JOURNAL_HOLD')
 lines=raw.splitlines()
 if len(lines)>MAX_RECORDS or any(len(line)>16384 for line in lines):raise JournalInvalid('JOURNAL_BOUND_HOLD')
 def unique(pairs):
  result={}
  for key,value in pairs:
   if key in result:raise ValueError('DUPLICATE_KEY')
   result[key]=value
  return result
 def nonfinite(_):raise ValueError('NONFINITE')
 rows=[];last='0'*64;nonces=set();jobs=set()
 for line in lines:
  try:
   row=json.loads(line.decode('utf-8'),object_pairs_hook=unique,parse_constant=nonfinite)
   if type(row) is not dict or set(row)!={'prev','event','hash'}:raise ValueError('ROW_SCHEMA')
  except (ValueError,TypeError,UnicodeError,RecursionError):raise JournalInvalid('JOURNAL_JSON_OR_SCHEMA_HOLD')
  event=row['event']
  if type(event) is not dict or set(event)!={'seq','nonce','job','digest','type'} or event['type']!='RESERVE' or type(event['seq']) is not int or event['seq']!=len(rows)+1 or not valid_id(event['nonce']) or not valid_id(event['job']) or not valid_hash(event['digest']):raise JournalInvalid('JOURNAL_EVENT_SCHEMA_HOLD')
  expected=hashlib.sha256((last+json.dumps(event,sort_keys=True,separators=(',',':'))).encode()).hexdigest()
  if not valid_hash(row['prev']) or not valid_hash(row['hash']) or row['prev']!=last or row['hash']!=expected:raise JournalInvalid('HASH_CHAIN_HOLD')
  if event['nonce'] in nonces or event['job'] in jobs:raise JournalInvalid('JOURNAL_HISTORY_REPLAY_HOLD')
  nonces.add(event['nonce']);jobs.add(event['job']);rows.append(event);last=expected
 return rows
class Journal:
 def __init__(self,root):
  self.root=pathlib.Path(root);self.root.mkdir(parents=True,exist_ok=True);self.log=self.root/"journal.jsonl";self.lock=self.root/"journal.lock"
 def transact(self,nonce,job,digest):
  if not valid_id(nonce) or not valid_id(job) or not valid_hash(digest):return 'INPUT_SCHEMA_HOLD'
  if msvcrt is None:return 'WINDOWS_LOCK_UNAVAILABLE_HOLD'
  try:return self._transact_locked(nonce,job,digest)
  except OSError:return 'JOURNAL_IO_HOLD'
 def _transact_locked(self,nonce,job,digest):
  with self.lock.open("a+b") as f:
   if f.seek(0,2)==0:f.write(b"\0");f.flush()
   f.seek(0)
   acquired=False
   for _ in range(100):
    try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1);acquired=True;break
    except OSError:time.sleep(.01)
   if not acquired:return "LOCK_TIMEOUT_HOLD"
   try:
    rows=[];last="0"*64
    if self.log.exists():
     with self.log.open('rb') as source:raw=source.read(MAX_BYTES+1)
     try:rows=validate_journal(raw)
     except JournalInvalid as error:return str(error)
     if rows:
      last='0'*64
      for event in rows:last=hashlib.sha256((last+json.dumps(event,sort_keys=True,separators=(',',':'))).encode()).hexdigest()
    if len(rows)>=MAX_RECORDS:return 'JOURNAL_BOUND_HOLD'
    if any(x["nonce"]==nonce or x["job"]==job for x in rows):return "REPLAY_REJECTED"
    event={"seq":len(rows)+1,"nonce":nonce,"job":job,"digest":digest,"type":"RESERVE"}
    row={"prev":last,"event":event};row["hash"]=hashlib.sha256((last+json.dumps(event,sort_keys=True,separators=(",",":"))).encode()).hexdigest()
    encoded=(json.dumps(row,sort_keys=True)+'\n').encode()
    if (self.log.stat().st_size if self.log.exists() else 0)+len(encoded)>MAX_BYTES:return 'JOURNAL_BOUND_HOLD'
    try:
     with self.log.open("ab") as out:out.write(encoded);out.flush();os.fsync(out.fileno())
    except OSError:return 'JOURNAL_WRITE_UNCERTAIN_HOLD'
    return "SHADOW_RESERVED"
   finally:
    f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
