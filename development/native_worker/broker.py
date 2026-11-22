"""DEV-only durable local coordinator. No server, cloud or production dispatch.

Every worker uses fixed test input and disposable, self-issued custody keys.
The SQLite ACK/commit records are DEV observations, not production R6/R10/R11.
"""
import argparse,base64,contextlib,hashlib,importlib.util,json,msvcrt,os,re,shutil,sqlite3,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SCENARIOS={'build_studio_dev'}
MAX_OPERATIONS=16
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def read_json(raw):
    def unique(pairs):
        data={}
        for key,value in pairs:
            if key in data:raise ValueError('DUPLICATE_JSON_KEY')
            data[key]=value
        return data
    return json.loads(raw,object_pairs_hook=unique)
def validate(req):
    if type(req) is not dict or set(req)!={'action','operation_id','scenario'}:raise ValueError('REQUEST_SCHEMA')
    if req['action'] not in ('submit','status'):raise ValueError('ACTION_DENIED')
    if type(req['operation_id']) is not str or not re.fullmatch('[a-f0-9]{32}',req['operation_id']):raise ValueError('OPERATION_ID_DENIED')
    if type(req['scenario']) is not str or req['scenario'] not in SCENARIOS:raise ValueError('SCENARIO_DENIED')
    return req
def verify_runtime():
    pins=read_json((ROOT/'BROKER-PINS.json').read_text())
    for item in pins['files']:
        path=(ROOT/item['path']).resolve()
        if not path.is_relative_to(ROOT) or sha(path)!=item['sha256']:raise ValueError('PINNED_RUNTIME_CHANGED:'+item['path'])
    if str(Path(sys.executable).resolve())!=pins['python']['path'] or sha(Path(sys.executable))!=pins['python']['sha256']:raise ValueError('PYTHON_PIN_CHANGED')
    return pins

def verify_inputs():
    pins=verify_runtime()
    config=read_json((ROOT/'WORKER-CONFIG.json').read_text())
    for item in config['files']:
        if sha(Path(item['path']))!=item['sha256']:raise ValueError('WORKER_CONFIG_PIN_CHANGED')
    if config['profile']!='DEV_UNSIGNED' or config['production_go'] is not False:raise ValueError('DEV_PROFILE_REQUIRED')
    for item in read_json((ROOT/'SOURCE-INPUTS.json').read_text())['files']:
        if sha(ROOT/item['path'])!=item['sha256']:raise ValueError('SOURCE_SNAPSHOT_CHANGED:'+item['path'])
    for item in read_json((ROOT/'DEPENDENCIES.json').read_text())['files']:
        if sha(ROOT/item['path'])!=item['sha256']:raise ValueError('OFFLINE_DEPENDENCY_CHANGED:'+item['path'])
    for item in read_json((ROOT/'TOOLS.json').read_text())['files']:
        if sha(Path(item['path']))!=item['sha256']:raise ValueError('TOOLCHAIN_CHANGED:'+item['role'])
    return pins

def response(state,**kwargs):
    return dict(schema='OpenRemaster.DevWorkflowResult.v1',state=state,production_go=False,
                independent_authority=False,engine='unsigned-studio-dev-build',**kwargs)
@contextlib.contextmanager
def database():
    db=sqlite3.connect(ROOT/'state/ledger.sqlite',timeout=1)
    try:
        db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE IF NOT EXISTS operations (id TEXT PRIMARY KEY, scenario TEXT NOT NULL, state TEXT NOT NULL, launches INTEGER NOT NULL CHECK(launches BETWEEN 0 AND 1), ack TEXT NOT NULL, result TEXT)')
        db.commit();yield db
    finally:db.close()
@contextlib.contextmanager
def writer():
    path=ROOT/'state/writer.lock';path.parent.mkdir(exist_ok=True)
    stream=path.open('a+b')
    try:
        if stream.seek(0,2)==0:stream.write(b'1');stream.flush()
        stream.seek(0)
        try:msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:yield False;return
        try:yield True
        finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
    finally:stream.close()
def row_response(row,replayed=False):
    if row[5] is not None:
        result=read_json(row[5]);result['replayed']=replayed;return result
    return response(row[2],operation_id=row[0],scenario=row[1],launch_count=row[3],ack=read_json(row[4]),replayed=replayed,commit=None)
def observe(req):
    if not (ROOT/'state/ledger.sqlite').exists():return response('NOT_FOUND',operation_id=req['operation_id'])
    with writer() as owned,database() as db:
        row=db.execute('SELECT * FROM operations WHERE id=?',(req['operation_id'],)).fetchone()
        if row is None:return response('NOT_FOUND',operation_id=req['operation_id'])
        if row[1]!=req['scenario']:return response('DENIED',reason='OPERATION_CONFLICT',operation_id=req['operation_id'])
        if owned and row[2] in ('ACKNOWLEDGED','STARTED'):
            result=response('HOLD',operation_id=row[0],scenario=row[1],launch_count=row[3],ack=read_json(row[4]),commit=None,reason='BROKER_ENDED_WITHOUT_COMMIT',automatic_retry=False)
            db.execute('UPDATE operations SET state=?,result=? WHERE id=?',('HOLD',json.dumps(result),row[0]));db.commit()
            return result
        return row_response(row,True)
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def validate_saved(result):
    if result.get('state')!='COMMITTED':return result
    operation=result['operation_id'];stage=ROOT/'state/operations'/operation
    actual=result['worker'];artifacts=actual['artifacts']
    if Path(artifacts['studio_exe']).resolve()!=(stage/'target/debug/openremaster_studio_shadow.exe').resolve():raise ValueError('SAVED_ARTIFACT_PATH_CHANGED')
    for name,field in [('studio_exe','studio_exe_sha256'),('frontend_index','frontend_index_sha256')]:
        if sha(Path(artifacts[name]))!=artifacts[field]:raise ValueError('SAVED_BUILD_ARTIFACT_CHANGED')
    if sha(stage/'artifacts.json')!=actual['artifacts_manifest_sha256']:raise ValueError('SAVED_ARTIFACT_MANIFEST_CHANGED')
    if digest(json.dumps(actual,sort_keys=True).encode())!=result['commit']['worker_result_sha256']:raise ValueError('SAVED_COMMIT_CHANGED')
    return result

def execute_worker(operation,scenario,pins):
    stage=ROOT/'state/operations'/operation;stage.mkdir(parents=True,exist_ok=False)
    source=stage/'source/studio';shutil.copytree(ROOT/'source/studio',source)
    tools=read_json((ROOT/'TOOLS.json').read_text())['paths']
    native=load(ROOT/'runtime/atomic_job_launcher.py','unified_owned_atomic')
    command=[tools['powershell'],'-NoLogo','-NoProfile','-NonInteractive','-File',str(ROOT/'build-studio.ps1'),'-OperationId',operation]
    started=time.monotonic()
    with (stage/'stdout.log').open('xb') as out,(stage/'stderr.log').open('xb') as err:
        with native.AtomicProcess(command,str(ROOT),out,err,headless=True) as owned:
            launch={'schema':'OpenRemaster.DevBuildLaunch.v1','operation_id':operation,'pid':owned.pid,'command':command,'build_plan_sha256':sha(ROOT/'BUILD-PLAN.json'),'source_manifest_sha256':sha(ROOT/'SOURCE-INPUTS.json'),'profile':'DEV_UNSIGNED','production_go':False}
            (stage/'launch.json').write_text(json.dumps(launch,indent=2))
            while owned.poll() is None:
                if time.monotonic()-started>2400:raise TimeoutError('DEV_BUILD_TIMEOUT')
                if os.fstat(out.fileno()).st_size+os.fstat(err.fileno()).st_size>64*1024*1024:raise ValueError('DEV_BUILD_LOG_LIMIT')
                time.sleep(.25)
            code=owned.returncode
    artifact_path=stage/'artifacts.json';artifacts=read_json(artifact_path.read_text(encoding='utf-8-sig')) if artifact_path.exists() else None
    success=code==0 and owned.tree_stopped and artifacts is not None and artifacts.get('signature_status')=='NotSigned' and artifacts.get('profile')=='DEV_UNSIGNED' and artifacts.get('production_go') is False
    verify_inputs()
    return {'wrapper_exit':code,'worker_state':'PASS' if success else 'HOLD','worker_pid':owned.pid,'owned_tree_stopped':owned.tree_stopped,'stage':str(stage),'elapsed_seconds':round(time.monotonic()-started,3),
            'source_manifest_sha256':sha(ROOT/'SOURCE-INPUTS.json'),'build_plan_sha256':sha(ROOT/'BUILD-PLAN.json'),'stdout_sha256':sha(stage/'stdout.log'),'stderr_sha256':sha(stage/'stderr.log'),
            'artifacts':artifacts,'artifacts_manifest_sha256':sha(artifact_path) if artifact_path.exists() else None,'success':success}

def submit(req,pins):
    (ROOT/'state').mkdir(exist_ok=True)
    with writer() as owned:
        if not owned:return response('BUSY',operation_id=req['operation_id'],reason='SINGLE_DEV_WRITER_ACTIVE',automatic_retry=False)
        with database() as db:
            row=db.execute('SELECT * FROM operations WHERE id=?',(req['operation_id'],)).fetchone()
            if row:
                if row[1]!=req['scenario']:return response('DENIED',reason='OPERATION_CONFLICT',operation_id=req['operation_id'])
                if row[2] in ('ACKNOWLEDGED','STARTED'):
                    result=response('HOLD',operation_id=row[0],scenario=row[1],launch_count=row[3],ack=read_json(row[4]),commit=None,reason='BROKER_ENDED_WITHOUT_COMMIT',automatic_retry=False)
                    db.execute('UPDATE operations SET state=?,result=? WHERE id=?',('HOLD',json.dumps(result),row[0]));db.commit();return result
                return row_response(row,True)
            if db.execute('SELECT COUNT(*) FROM operations').fetchone()[0]>=MAX_OPERATIONS:return response('DENIED',reason='DEV_OPERATION_QUOTA')
            ack={'schema':'OpenRemaster.DevAck.v1','operation_id':req['operation_id'],'scenario':req['scenario'],'request_sha256':digest(json.dumps(req,sort_keys=True).encode()),'persisted':True,'authority':'LOCAL_TEST_LEDGER_ONLY','build_plan_sha256':sha(ROOT/'BUILD-PLAN.json')}
            db.execute('INSERT INTO operations VALUES (?,?,?,?,?,NULL)',(req['operation_id'],req['scenario'],'ACKNOWLEDGED',0,json.dumps(ack)));db.commit()
            if req['scenario']=='crash_after_ack':os._exit(91)
            db.execute('UPDATE operations SET state=?,launches=1 WHERE id=?',('STARTED',req['operation_id']));db.commit()
            try:
                actual=execute_worker(req['operation_id'],req['scenario'],pins)
                result=response('COMMITTED' if actual['success'] else 'HOLD',operation_id=req['operation_id'],scenario=req['scenario'],launch_count=1,ack=ack,worker=actual,automatic_retry=False,replayed=False)
                result['commit']={'schema':'OpenRemaster.DevCommit.v1','operation_id':req['operation_id'],'worker_result_sha256':digest(json.dumps(actual,sort_keys=True).encode()),'authority':'LOCAL_TEST_LEDGER_ONLY','build_plan_sha256':sha(ROOT/'BUILD-PLAN.json')} if actual['success'] else None
            except Exception as error:
                result=response('HOLD',operation_id=req['operation_id'],scenario=req['scenario'],launch_count=1,ack=ack,commit=None,reason=type(error).__name__+':'+str(error),automatic_retry=False)
            db.execute('UPDATE operations SET state=?,result=? WHERE id=?',(result['state'],json.dumps(result),req['operation_id']));db.commit()
            return result
def dispatch(req):
    req=validate(req);pins=verify_inputs()
    return observe(req) if req['action']=='status' else submit(req,pins)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--request',required=True);args=parser.parse_args()
    try:
        if len(args.request.encode())>4096:raise ValueError('REQUEST_SIZE')
        req=validate(read_json(args.request));verify_runtime()
        host=load(ROOT/'host.py','unified_client_host');host.setup()
        result=host.submit(req['operation_id']) if req['action']=='submit' else host.external_status(req['operation_id'])
    except Exception as error:result=response('DENIED',reason=type(error).__name__+':'+str(error),automatic_retry=False)
    print(json.dumps(result,separators=(',',':')))
if __name__=='__main__':main()
