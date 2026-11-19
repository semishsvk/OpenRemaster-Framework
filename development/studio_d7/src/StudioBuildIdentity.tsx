declare const __STUDIO_BUILD__: {version: string; commit: string | null; builtAt: string | null};

export function StudioBuildIdentity() {
  const {version, commit, builtAt} = __STUDIO_BUILD__;
  return <section className="panel" aria-label="Studio build identity">
    <h2>Studio build</h2>
    <dl className="studio-build-identity">
      <dt>Version</dt><dd>{version}</dd>
      <dt>Commit</dt><dd>{commit ? <code>{commit}</code> : "Unavailable"}</dd>
      <dt>Build date (UTC)</dt><dd>{builtAt ? <time dateTime={builtAt}>{builtAt}</time> : "Unavailable"}</dd>
    </dl>
  </section>;
}
