import {useEffect, useMemo, useRef, useState} from 'react';
import {observationProjectInput, parseNativeFileObservation, validateObservationBinding, type ObservationBinding, type ObservationRequest} from './native-file-observation';
import {projectWorkspaceView, type ProjectObservationView} from './project-workspace-view';

export type ProjectObservationReader = (selection: ObservationRequest) => Promise<unknown>;
type Props = {binding?: ObservationBinding | null; read?: ProjectObservationReader};
type View = ProjectObservationView | null;

/** The native bridge is supplied only by the admitted existing Host adapter.
 * No guessed IPC action, arbitrary file read, report fallback or executor lives
 * here. Until its catalog/producer contract is accepted, no reader is attached.
 */
export function ProjectWorkspace({binding = null, read}: Props) {
  const [view, setView] = useState<View>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [held, setHeld] = useState(false);
  const [now, setNow] = useState(Date.now);
  const generation = useRef(0);
  const active = useMemo(() => {
    try { const selected = binding ? validateObservationBinding(binding) : null;
      return selected ? {selected, key: JSON.stringify(selected)} : null;
    } catch { return null; }
  }, [binding]);

  useEffect(() => {
    const current = ++generation.current;
    let mounted = true, pending = false;
    setView(null); setFailed(false); setHeld(false); setBusy(false);
    const request = async () => {
      if (!read || !active || pending) return;
      pending = true; setBusy(true);
      try {
        const raw = await read(Object.freeze({...active.selected.request}));
        if (!mounted || generation.current !== current) return;
        const observedAt = Date.now();
        const observed = parseNativeFileObservation(raw, active.selected, observedAt);
        const parsed = observationProjectInput(observed, active.selected, observedAt);
        setView(parsed ? {input: parsed, key: active.key} : null); setHeld(!parsed);
        setFailed(false); setNow(observedAt);
      } catch {
        if (mounted && generation.current === current) { setView(null); setFailed(true); }
      } finally {
        pending = false;
        if (mounted && generation.current === current) setBusy(false);
      }
    };
    void request();
    const poll = setInterval(() => { setNow(Date.now()); void request(); }, 5_000);
    return () => { mounted = false; generation.current++; clearInterval(poll); };
  }, [active, read]);

  // Recompute freshness at every tick; a once-valid cached build must expire.
  const shown = projectWorkspaceView(view, active?.key ?? null, now);
  const phase = !read || !active || failed || held ? 'HOLD' : shown?.phase ?? 'UNKNOWN';
  const playable = phase === 'LIVE' ? shown?.playableBuild : null;
  return <section className="panel" aria-labelledby="project-workspace-title">
    <div className="panel-eyebrow">PROJECT WORKSPACE / READ ONLY</div>
    <h2 id="project-workspace-title">Current project evidence</h2>
    <p role="status" aria-live="polite">{phase}{busy ? ' · Reading current evidence…' : ''}</p>
    {!read && <p>The native file observation adapter is awaiting its accepted catalog and producer contract.</p>}
    {read && !active && <p>No project and edition selection has been verified.</p>}
    {held && <p>The native producer held this selection without claiming a physical build.</p>}
    {failed && <p>Current project evidence is unavailable or invalid. No previous response is treated as current.</p>}
    <dl className="studio-build-identity">
      <dt>Project / edition</dt><dd>{active ? active.selected.request.project_id + ' / ' + active.selected.request.edition_id : 'UNKNOWN'}</dd>
      <dt>Physical build</dt><dd>{playable ? playable.id : 'UNVERIFIED'}</dd>
      <dt>Source commit</dt><dd><code>{shown?.sourceCheckpoint?.commit ?? 'UNKNOWN'}</code></dd>
      <dt>Source tree</dt><dd><code>{shown?.sourceCheckpoint?.tree ?? 'UNKNOWN'}</code></dd>
      <dt>Gameplay</dt><dd>{phase === 'LIVE' ? shown?.gameplay ?? 'UNKNOWN' : 'HOLD'}</dd>
      <dt>Fidelity</dt><dd>{phase === 'LIVE' ? shown?.fidelity ?? 'UNKNOWN' : 'HOLD'}</dd>
      <dt>Execution admission</dt><dd>{phase === 'LIVE' ? shown?.executionAdmission ?? 'UNKNOWN' : 'HOLD'}</dd>
      <dt>Last physical verification</dt><dd>{phase === 'LIVE' && shown?.lastVerifiedAt !== null && shown?.lastVerifiedAt !== undefined ? new Date(shown.lastVerifiedAt).toISOString() : 'UNVERIFIED'}</dd>
    </dl>
    <p>This view issues no execution permission. File presence, gameplay and fidelity are separate observations.</p>
    {shown?.blockers.length ? <ul>{shown.blockers.map((reason, index) => <li key={index}>{reason}</li>)}</ul> : null}
    {shown?.nextSafeTask && <p>Next recorded task: {shown.nextSafeTask}</p>}
  </section>;
}
