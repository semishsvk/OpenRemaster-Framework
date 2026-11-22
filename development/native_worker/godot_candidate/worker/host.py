"""Local headless DEV queue. Fixed synthetic Godot project only; no production dispatch or network."""
import argparse, contextlib, ctypes, hashlib, importlib.util, json, msvcrt, os
from pathlib import Path
import re, subprocess, sys, time, uuid, threading
ROOT=Path(__file__).resolve().parent
CANDIDATE=ROOT
STATE=ROOT/'host-state'
MAX_SECONDS=28800
MAX_JOBS=16

def read(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,value):
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    with temp.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2);stream.flush();os.fsync(stream.fileno())
    for attempt in range(6):
        try:os.replace(temp,path);break
        except OSError as error:
            if getattr(error,'winerror',None) not in (5,32,33) or attempt==5:raise
            time.sleep(min(.05*(2**attempt),.4))

def setup():
    for name in ('pending','running','done','requests','evidence'):
        (STATE/name).mkdir(parents=True,exist_ok=True)

@contextlib.contextmanager
def lock(name):
    with (STATE/name).open('a+b') as stream:
        if stream.seek(0,2)==0: stream.write(b'1');stream.flush()
        stream.seek(0)
        try: msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        except OSError: yield False;return
        try: yield True
        finally: stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)

def identity(pid):
    from ctypes import wintypes as W
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
    k.GetProcessTimes.argtypes=[W.HANDLE]+[ctypes.POINTER(W.FILETIME)]*4
    k.GetExitCodeProcess.argtypes=[W.HANDLE,ctypes.POINTER(W.DWORD)]
    k.CloseHandle.argtypes=[W.HANDLE]
    handle=k.OpenProcess(0x1000,False,pid)
    if not handle:return None
    try:
        fields=[W.FILETIME() for _ in range(4)];code=W.DWORD()
        if not k.GetProcessTimes(handle,*(ctypes.byref(x) for x in fields)):return None
        if not k.GetExitCodeProcess(handle,ctypes.byref(code)) or code.value!=259:return None
        return (fields[0].dwHighDateTime<<32)|fields[0].dwLowDateTime
    finally:k.CloseHandle(handle)

def broker():
    spec=importlib.util.spec_from_file_location('isolated_dev_broker',CANDIDATE/'broker.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.verify_inputs();return module

def health():
    path=STATE/'heartbeat.json'
    if not path.exists():return dict(state='STOPPED',healthy=False,production_go=False)
    beat=read(path)
    with lock('host.lock') as available:
        alive=not available and beat['process_created'] is not None and identity(beat['pid'])==beat['process_created']
    beat['healthy']=alive and 0<=time.time()-beat['updated_epoch']<=6 and beat['state'] in ('IDLE','RUNNING','STARTING')
    beat['process_alive']=alive
    return beat

def daemon():
    with lock('host.lock') as acquired:
        if not acquired:return dict(state='BUSY',reason='ONE_DEV_HOST_ONLY')
        generation=uuid.uuid4().hex;started=time.monotonic();jobs=0
        beat=dict(schema='OpenRemaster.IsolatedDevHost.v1',generation=generation,pid=os.getpid(),
                  process_created=identity(os.getpid()),production_go=False,engine='unsigned-studio-dev-build')
        monitor_stop=threading.Event();monitor_lock=threading.Lock()
        def pulse(state,**details):
            with monitor_lock:
                beat.update(state=state,updated_epoch=time.time(),jobs_processed=jobs,**details)
                write(STATE/'heartbeat.json',beat)
        def refresh():
            while not monitor_stop.wait(1):
                with monitor_lock:
                    beat['updated_epoch']=time.time();write(STATE/'heartbeat.json',beat)
        pulse('STARTING')
        monitor=threading.Thread(target=refresh,daemon=True);monitor.start()
        try:
            api=broker()
            # Claim files survive a host crash. Only query the ledger; never resubmit.
            for path in sorted((STATE/'running').glob('*.json')):
                req=api.validate(read(path))
                if req['action']!='submit' or path.stem!=req['operation_id']:raise ValueError('RECOVERY_REQUEST_BINDING_CHANGED')
                result=api.dispatch(dict(req,action='status'))
                if result['state'] in ('NOT_FOUND','ACKNOWLEDGED','STARTED'):
                    result=dict(state='HOLD',reason='ORPHAN_CLAIM_NO_REEXECUTION',operation_id=req['operation_id'],scenario=req['scenario'],production_go=False)
                write(STATE/'done'/path.name,result)
                path.rename(STATE/'evidence'/(path.stem+'.recovered.'+generation+'.json'))
                if result['state']!='COMMITTED':
                    pulse('HOLD',reason='RECOVERY_REQUIRES_DIAGNOSIS');return beat
            while time.monotonic()-started<MAX_SECONDS and jobs<MAX_JOBS:
                stop=STATE/'stop.json'
                if stop.exists() and read(stop).get('generation')==generation:
                    pulse('STOPPED',reason='USER_STOP');return beat
                pulse('IDLE',operation_id=None)
                pending=sorted((STATE/'pending').glob('*.json'))
                if not pending:time.sleep(.5);continue
                path=pending[0];claimed=STATE/'running'/path.name
                path.rename(claimed)
                req=api.validate(read(claimed))
                if req['action']!='submit' or req['scenario'] not in api.SCENARIOS or path.stem!=req['operation_id']:
                    raise ValueError('QUEUE_REQUEST_DENIED')
                pulse('RUNNING',operation_id=req['operation_id'])
                result=api.dispatch(req)
                write(STATE/'done'/path.name,result)
                claimed.rename(STATE/'evidence'/(path.stem+'.processed.'+generation+'.json'))
                jobs+=1
                if result['state']!='COMMITTED':
                    pulse('HOLD',reason='RESULT_REQUIRES_DIAGNOSIS');return beat
            pulse('STOPPED',reason='FINITE_RUN_LIMIT');return beat
        except BaseException as error:
            pulse('HOLD',reason=repr(error));raise
        finally:
            monitor_stop.set();monitor.join(timeout=2)

def external_status(operation):
    if not re.fullmatch('[a-f0-9]{32}',operation):raise ValueError('INVALID_OPERATION_ID')
    done=STATE/'done'/(operation+'.json');marker=STATE/'requests'/(operation+'.json')
    marker_present=marker.exists();request=read(marker) if marker_present else None
    if marker_present and (type(request) is not dict or request.get('operation_id')!=operation or request.get('scenario') not in ('build_studio_dev','build_godot_dev')):raise ValueError('REQUEST_MARKER_BINDING_CHANGED')
    if done.exists():
        if request is None:raise ValueError('SAVED_RESULT_REQUEST_MARKER_MISSING')
        result=read(done)
        if type(result) is not dict or result.get('operation_id')!=operation or result.get('scenario')!=request['scenario']:raise ValueError('SAVED_QUEUE_RESULT_BINDING_CHANGED')
        api=broker();return dict(api.validate_saved(result),replayed=True)
    if not marker.exists():return dict(schema='OpenRemaster.DevWorkflowResult.v1',state='NOT_FOUND',operation_id=operation,production_go=False)
    if not (STATE/'pending'/(operation+'.json')).exists() and not (STATE/'running'/(operation+'.json')).exists():
        return dict(schema='OpenRemaster.DevWorkflowResult.v1',state='HOLD',operation_id=operation,reason='INTERRUPTED_QUEUE_PUBLICATION_NO_RETRY',production_go=False,automatic_retry=False)
    status=health()
    if not status.get('healthy'):
        return dict(schema='OpenRemaster.DevWorkflowResult.v1',state='HOLD',operation_id=operation,reason='WORKER_NOT_HEALTHY_QUERY_PRESERVED_EVIDENCE',production_go=False,automatic_retry=False)
    running=(STATE/'running'/(operation+'.json')).exists()
    result=dict(request,state='RUNNING' if running else 'QUEUED',launch_count=1 if running else 0,replayed=True)
    progress=CANDIDATE/'state/operations'/operation/'build-progress.json'
    if progress.exists():result['progress']=read(progress)
    return result

def submit(operation,scenario='build_studio_dev'):
    if scenario not in ('build_studio_dev','build_godot_dev'):raise ValueError('SCENARIO_DENIED')
    operation=operation or uuid.uuid4().hex
    if not re.fullmatch('[a-f0-9]{32}',operation):raise ValueError('INVALID_OPERATION_ID')
    with lock('submit.lock') as acquired:
        if not acquired:return dict(schema='OpenRemaster.DevWorkflowResult.v1',state='BUSY',production_go=False,automatic_retry=False)
        marker=STATE/'requests'/(operation+'.json')
        if marker.exists():
            if read(marker).get('scenario')!=scenario:raise ValueError('OPERATION_SCENARIO_CONFLICT')
            return external_status(operation)
        if not health()['healthy']:raise RuntimeError('DEV_HOST_NOT_HEALTHY')
        if len(list((STATE/'requests').glob('*.json')))>=MAX_JOBS:raise RuntimeError('DEV_QUEUE_QUOTA')
        req=dict(action='submit',operation_id=operation,scenario=scenario)
        ack=dict(schema='OpenRemaster.DevQueueAck.v1',operation_id=operation,persisted=True,authority='LOCAL_DEV_QUEUE_ONLY')
        result=dict(schema='OpenRemaster.DevWorkflowResult.v1',state='QUEUED',operation_id=operation,scenario=scenario,launch_count=0,ack=ack,commit=None,production_go=False,profile='DEV_UNSIGNED',replayed=False)
        write(marker,result);write(STATE/'pending'/(operation+'.json'),req)
        return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['start','daemon','status','stop','submit','result'])
    parser.add_argument('--operation-id');parser.add_argument('--expected-config-sha');args=parser.parse_args();setup()
    if args.action in ('daemon','start'):
        config=ROOT/'WORKER-CONFIG.json'
        if not args.expected_config_sha or hashlib.sha256(config.read_bytes()).hexdigest()!=args.expected_config_sha:raise RuntimeError('COMPILED_NATIVE_WORKER_ENTRY_REQUIRED')
        return daemon()
    if args.action=='status':return health()
    if args.action=='stop':
        current=health()
        if not current.get('process_alive'):return current
        write(STATE/'stop.json',dict(generation=current['generation']))
        if current.get('state')=='RUNNING':return dict(current,stop_requested=True)
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            current=health()
            if not current.get('process_alive'):return current
            time.sleep(.1)
        raise RuntimeError('STOP_PENDING_NO_FORCED_KILL')
    if args.action=='submit':return submit(args.operation_id)
    if not args.operation_id or not re.fullmatch('[a-f0-9]{32}',args.operation_id):raise ValueError('RESULT_REQUIRES_VALID_OPERATION_ID')
    return external_status(args.operation_id)

if __name__=='__main__':
    try:
        result=main();print(json.dumps(result))
        if result.get("state")=="HOLD":sys.exit(75)
    except Exception as error:print(json.dumps(dict(state='ERROR',reason=str(error),automatic_retry=False,production_go=False)));sys.exit(1)


