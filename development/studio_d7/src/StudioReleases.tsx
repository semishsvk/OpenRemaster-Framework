import {useEffect, useRef, useState, type MouseEvent} from 'react';
import {fetchReleaseJson, parseReleaseCi, parseStudioReleases, releasesEndpoint, repository, verifyReleaseFile, type StudioRelease} from './studio-releases';
import type {} from './dev-worker';
declare const __STUDIO_BUILD__: {version: string; commit: string | null; builtAt: string | null};

export default function StudioReleases() {
  const [releases, setReleases] = useState<StudioRelease[]>([]);
  const [selected, setSelected] = useState('');
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState('Check GitHub to load the latest published DEV previews.');
  const [ci, setCi] = useState('CI has not been checked');
  const [verification, setVerification] = useState('');
  const [checkingFile, setCheckingFile] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const revision = useRef(0);
  const release = releases.find(item => item.tag === selected);
  useEffect(() => () => { controller.current?.abort(); revision.current++; }, []);

  async function check() {
    controller.current?.abort();
    const request = new AbortController(); controller.current = request;
    const timer = setTimeout(() => request.abort(), 15000);
    revision.current++; setReleases([]); setSelected(''); setVerification(''); setCheckingFile(false); setCi('CI has not been checked');
    setBusy(true); setStatus('Checking GitHub…');
    try {
      const list = parseStudioReleases(await fetchReleaseJson(releasesEndpoint, request.signal));
      if (request.signal.aborted) return;
      setReleases(list); setSelected(list[0]?.tag ?? '');
      setStatus(list.length ? `GitHub checked at ${new Date().toISOString()}` : 'No Windows DEV preview is available in the latest five releases.');
    } catch (reason) { if (controller.current === request) setStatus(`Release check failed. ${String(reason)}`); }
    finally { clearTimeout(timer); if (controller.current === request) setBusy(false); }
  }
  useEffect(() => {
    setCi('CI has not been checked');
    if (!release?.runId) return;
    const request = new AbortController(), timer = setTimeout(() => request.abort(), 15000);
    void fetchReleaseJson(`https://api.github.com/repos/semishsvk/OpenRemaster-Framework/actions/runs/${release.runId}`, request.signal)
      .then(raw => { if (!request.signal.aborted) setCi(parseReleaseCi(raw, release)); })
      .catch(reason => { if (!request.signal.aborted) setCi(`CI verification unavailable. ${String(reason)}`); })
      .finally(() => clearTimeout(timer));
    return () => { request.abort(); clearTimeout(timer); };
  }, [release]);

  async function open(event: MouseEvent<HTMLAnchorElement>, url: string) {
    const invoke = window.__TAURI_INTERNALS__?.invoke;
    if (!invoke) return;
    event.preventDefault();
    try { await invoke('studio_open_release', {url}); }
    catch (reason) { setStatus(`Could not open link. ${String(reason)}`); }
  }
  async function verify(file?: File) {
    if (!file || !release?.digest) return;
    const current = ++revision.current, expected = release.digest;
    setCheckingFile(true); setVerification('Computing SHA-256 locally…');
    try {
      const actual = await verifyReleaseFile(file, expected);
      if (revision.current === current) setVerification(`Checksum matches GitHub release metadata. SHA-256 ${actual}`);
    } catch (reason) { if (revision.current === current) setVerification(String(reason)); }
    finally { if (revision.current === current) setCheckingFile(false); }
  }
  return <section className="panel" aria-label="Studio DEV releases" style={{padding:24,marginBottom:24,overflowWrap:'anywhere'}}>
    <h2>Studio DEV releases</h2>
    <p>Installed version <strong>{__STUDIO_BUILD__.version}</strong> · source <code>{__STUDIO_BUILD__.commit ?? 'Unavailable'}</code></p>
    <button disabled={busy} onClick={() => void check()}>Check DEV releases</button>
    <p role="status">{status}</p>
    {releases.length > 0 && <label>Published preview <select style={{maxWidth:'100%'}} value={selected} onChange={event => { revision.current++; setSelected(event.target.value); setVerification(''); setCheckingFile(false); }}>
      {releases.map(item => <option key={item.tag} value={item.tag}>{item.published} · {item.commit.slice(0,12)}</option>)}
    </select></label>}
    {release && <>
      <p>{release.commit === __STUDIO_BUILD__.commit ? 'This preview matches the installed source commit.' : 'This preview has a different source commit.'}</p>
      <p>{ci}</p><p>Published <time dateTime={release.published}>{release.published}</time></p>
      <p><a href={release.page} target="_blank" rel="noopener noreferrer" onClick={event => void open(event, release.page)}>Release notes on GitHub</a> · <a href={release.download} target="_blank" rel="noopener noreferrer" onClick={event => void open(event, release.download)}>Download Windows DEV ZIP</a></p>
      <details><summary>Changes and release notes</summary><pre style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{release.notes || 'No release notes supplied.'}</pre></details>
      <p>GitHub archive SHA-256 <code>{release.digest ?? 'Unavailable for this release'}</code></p>
      {release.digest && <label>Verify downloaded ZIP <input style={{maxWidth:'100%'}} type="file" accept=".zip" disabled={checkingFile} onChange={event => { void verify(event.target.files?.[0]); event.target.value = ''; }}/></label>}
      <p role="status" aria-live="polite">{verification}</p>
      <small>File verification runs locally. These previews are unsigned; the checksum binds the file to GitHub metadata.</small>
    </>}
    <p><a href={`${repository}/releases`} target="_blank" rel="noopener noreferrer" onClick={event => void open(event, `${repository}/releases`)}>All published releases</a></p>
  </section>;
}
