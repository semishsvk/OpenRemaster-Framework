import {useCallback, useEffect, useRef, useState} from 'react';
import {activeStates, canStartAnother, operationKey, parseCapabilities, parseDevResult, phaseLabels, readOperation, saveOperation, type Capabilities, type DevResult} from './dev-worker';

export default function DevWorkerPanel() {
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [capabilityError, setCapabilityError] = useState('');
  const [operation, setOperation] = useState('');
  const [result, setResult] = useState<DevResult | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [storageReady, setStorageReady] = useState(false);
  const pending = useRef(false);
  const currentOperation = useRef('');
  const mounted = useRef(false);
  const scope = capabilities?.worker_scope ?? 'portable-ui';

  const query = useCallback(async (id: string, workerScope: string) => {
    if (pending.current) return;
    pending.current = true; setBusy(true); setError('');
    try {
      const invoke = window.__TAURI_INTERNALS__?.invoke;
      if (!invoke) throw Error('Native worker connection is unavailable');
      const raw = await invoke('dev_worker_call', {request: {action: 'status', operation_id: id, scenario: 'build_studio_dev'}});
      const value = parseDevResult(raw, id);
      if (!mounted.current || currentOperation.current !== id) return;
      saveOperation(localStorage, workerScope, id, value);
      setResult(value);
    } catch (reason) {
      if (mounted.current && currentOperation.current === id) { setResult(null); setError(String(reason)); }
    } finally { pending.current = false; if (mounted.current) setBusy(false); }
  }, []);

  useEffect(() => {
    mounted.current = true;
    async function connect() {
      try {
        const invoke = window.__TAURI_INTERNALS__?.invoke;
        if (!invoke) throw Error('Open the native Studio app to inspect DEV worker capabilities.');
        const value = parseCapabilities(await invoke('studio_capabilities'));
        if (!mounted.current) return;
        setCapabilities(value);
        const workerScope = value.worker_scope ?? 'portable-ui';
        const saved = readOperation(localStorage, workerScope);
        const probe = `${operationKey(workerScope)}-storage-probe`;
        localStorage.setItem(probe, '1'); localStorage.removeItem(probe);
        setStorageReady(true);
        if (saved) {
          currentOperation.current = saved.operation; setOperation(saved.operation);
          if (value.worker_ready) await query(saved.operation, workerScope);
        }
      } catch (reason) { if (mounted.current) setCapabilityError(String(reason)); }
    }
    void connect();
    return () => { mounted.current = false; };
  }, [query]);

  useEffect(() => {
    if (!capabilities?.worker_ready || !operation || !activeStates.includes(result?.state ?? '')) return;
    const timer = setInterval(() => void query(operation, scope), 10000);
    return () => clearInterval(timer);
  }, [capabilities?.worker_ready, operation, result?.state, query, scope]);

  useEffect(() => {
    function changed(event: StorageEvent) {
      if (event.key !== operationKey(scope)) return;
      try {
        const saved = readOperation(localStorage, scope);
        if (!saved || saved.operation === currentOperation.current) return;
        currentOperation.current = saved.operation; setOperation(saved.operation); setResult(null);
        setError('Another Studio window selected an operation. Refresh its saved status.');
      } catch (reason) { setStorageReady(false); setError(String(reason)); }
    }
    window.addEventListener('storage', changed);
    return () => window.removeEventListener('storage', changed);
  }, [scope]);

  async function submit() {
    if (pending.current || !capabilities?.worker_ready || !storageReady) return;
    if (!navigator.locks) { setError('This WebView needs Web Locks support to coordinate DEV submissions.'); return; }
    pending.current = true; setBusy(true); setError('');
    try {
      await navigator.locks.request(`orf-studio-submit-${scope}`, {ifAvailable: true}, async lock => {
        if (!lock) throw Error('Another Studio window is submitting a build. Refresh status.');
        const saved = readOperation(localStorage, scope);
        if (saved && !canStartAnother(saved.result)) throw Error('Resolve the saved operation before starting another build.');
        const id = crypto.randomUUID().replaceAll('-', '');
        saveOperation(localStorage, scope, id, null);
        currentOperation.current = id; setOperation(id); setResult(null);
        const invoke = window.__TAURI_INTERNALS__?.invoke;
        if (!invoke) throw Error('Native worker connection is unavailable');
        const raw = await invoke('dev_worker_call', {request: {action: 'submit', operation_id: id, scenario: 'build_studio_dev'}});
        const value = parseDevResult(raw, id);
        saveOperation(localStorage, scope, id, value);
        if (mounted.current && currentOperation.current === id) setResult(value);
      });
    } catch (reason) { if (mounted.current) { setResult(null); setError(String(reason)); } }
    finally { pending.current = false; if (mounted.current) setBusy(false); }
  }

  const ready = capabilities?.worker_ready === true;
  const artifact = result?.state === 'COMMITTED' ? result.worker?.artifacts : undefined;
  return <section className="panel" aria-label="Studio DEV operation" data-testid="dev-worker-panel" style={{padding:24,marginBottom:24}}>
    <div className="eyebrow">DEV UNSIGNED</div><h2>Studio DEV build</h2>
    <p>{capabilities?.reason ?? (capabilityError || 'Checking native capabilities…')}</p>
    {capabilities && capabilityError && <p role="alert">{capabilityError}</p>}
    {capabilities && <p>DEV worker: <strong>{ready ? 'available' : 'unavailable'}</strong></p>}
    <div style={{display:'flex',gap:12,flexWrap:'wrap'}}>
      <button data-testid="dev-run" disabled={busy || !ready || !storageReady || (!!operation && !canStartAnother(result))} onClick={() => void submit()}>Build a DEV candidate</button>
      <button data-testid="dev-status" disabled={busy || !ready || !operation} onClick={() => void query(operation, scope)}>Refresh build status</button>
    </div>
    <p>Operation: <code>{operation || 'none'}</code></p>
    <div role="status" aria-live="polite">{busy ? 'Checking operation…' : phaseLabels[result?.state ?? ''] ?? (operation ? 'Saved outcome needs verification' : 'Ready')}</div>
    {error && <p role="alert">{error}</p>}
    {result?.reason && <p>Reason: {result.reason}</p>}
    {result && <p>Launches: {result.launch_count ?? 'unconfirmed'} · ACK: {result.ack ? 'recorded' : 'pending'} · Commit: {result.commit ? 'recorded' : 'pending'}</p>}
    {artifact && <dl className="studio-build-identity"><dt>Artifact</dt><dd><code>{artifact.studio_exe}</code></dd><dt>SHA-256</dt><dd><code>{artifact.studio_exe_sha256}</code></dd></dl>}
    {Object.entries(result?.logs ?? {}).map(([name, log]) => <details key={name}><summary>{name} · last 8 KiB</summary><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere',maxHeight:300,overflow:'auto'}}>{log || 'No output yet'}</pre></details>)}
    <small>Active operation status refreshes every 10 seconds. Saved operations resume status checks after reopening Studio. Unknown outcomes remain on hold.</small>
  </section>;
}
