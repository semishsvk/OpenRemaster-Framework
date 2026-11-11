import {Fragment, useId} from "react";
import acceptance from "./data/openazrael-candidate-v205-iter2-acceptance.json";
import readmeCheck from "./data/openazrael-candidate-v205-iter2-readme-check.json";
import packageReport from "./data/openazrael-v250-build.json";
import packageReadmeCheck from "./data/openazrael-v250-readme-check.json";

type BuildReportSource = {
  projectId: string;
  checkpoint: string;
  sourceRelativePath: string;
  sourceSha256: string;
};

const checkLabels = {
  physical_transitions: "Room transitions",
  full_demo: "Demo playthrough",
  inventory_hud: "Inventory HUD",
  object_visibility: "Object visibility",
  save_compat: "Save compatibility",
  interaction_cursor: "Interaction cursor",
  production_flythrough: "Flythrough",
  clean_install_startup: "Clean install startup",
} satisfies Record<keyof typeof acceptance.gates, string>;

const sharedChecks = {
  physical_transitions: "Physical PPPV transitions",
  full_demo: "Full demo",
  inventory_hud: "Inventory/HUD",
  save_compat: "Save/load",
  interaction_cursor: "Cursor/interactions",
  clean_install_startup: "Clean install / startup",
} satisfies Partial<Record<keyof typeof checkLabels, string>>;

function readCheck(value: string) {
  if (value === "PASS_EXIT_0") return {status: "PASS"};
  const separator = value.indexOf(" ");
  if (separator < 0) return {status: "UNKNOWN"};
  try {
    const result = JSON.parse(value.slice(separator + 1));
    return {
      status: ["PASS", "FAIL", "HOLD"].includes(result?.status) ? result.status : "UNKNOWN",
      version: Number.isSafeInteger(result?.version) ? result.version : undefined,
    };
  } catch {
    return {status: "UNKNOWN"};
  }
}

function formatArchivedCheck(key: keyof typeof checkLabels) {
  const {status, version} = readCheck(acceptance.gates[key]);
  return version === undefined ? status : `${status} (reported test v${version})`;
}

function BuildCheckComparison({olderBuildId}: {olderBuildId: string}) {
  return <details>
    <summary>Compare reported checks</summary>
    <p>Each column shows the result recorded by its build report. Check scope may differ by build.</p>
    <table className="build-check-comparison">
      <caption>Archived check comparison</caption>
      <thead><tr>
        <th scope="col">Check</th>
        <th scope="col">{olderBuildId}</th>
        <th scope="col">{packageReport.buildId}</th>
      </tr></thead>
      <tbody>
        {(Object.keys(sharedChecks) as Array<keyof typeof sharedChecks>).map(key => {
          const prefix = `${sharedChecks[key]} `;
          const result = packageReport.checks.find(check => check.startsWith(prefix));
          return <tr key={key}>
            <th scope="row">{checkLabels[key]}</th>
            <td>{formatArchivedCheck(key)}</td>
            <td>{result?.slice(prefix.length) ?? "UNKNOWN"}</td>
          </tr>;
        })}
      </tbody>
    </table>
  </details>;
}

function BuildReadmeStatus({check}: {check: typeof readmeCheck | typeof packageReadmeCheck | null}) {
  return <>
    <dl>
      <dt>Build README</dt>
      <dd>{check?.status ?? "UNKNOWN"}{check?.status === "README_GATE_PASS" ? " (structural check)" : ""}</dd>
    </dl>
    {check && <>
      {check.problems.length > 0 && <ul>{check.problems.map((problem, index) =>
        <li key={index}>{problem}</li>)}</ul>}
      <p>Archived package checked <time dateTime={check.checkedAt}>{check.checkedAt.replace("T", " ").replace("+00:00", " UTC")}</time>
        {" using "}<code>{check.validator}</code>.</p>
    </>}
  </>;
}

export function BuildStatusOverview({records}: {records: readonly BuildReportSource[]}) {
  const archiveGroup = useId();
  const source = records.find(record => record.projectId === "OpenAzrael" &&
    record.checkpoint === acceptance.candidate &&
    record.sourceSha256 === "16ed66f786a84a8c19285aaa4547c78a1c498e03e8752fca15cd30fcaf25ca3a");
  const documentation = source && readmeCheck.schema === "OpenRemaster.StudioReadmeCheck.v1" &&
    readmeCheck.projectId === source.projectId && readmeCheck.buildId === source.checkpoint &&
    readmeCheck.acceptanceSha256 === source.sourceSha256 ? readmeCheck : null;
  const packageDocumentation = packageReadmeCheck.schema === "OpenRemaster.StudioReadmeCheck.v1" &&
    packageReadmeCheck.projectId === packageReport.projectId && packageReadmeCheck.buildId === packageReport.buildId &&
    packageReadmeCheck.packageManifestSha256 === packageReport.packageManifestSha256 ? packageReadmeCheck : null;

  return <section className="portfolio-evidence" aria-label="Build status">
    <div className="portfolio-evidence-heading"><h5>Build status</h5><span className="tag tag-hold">HOLD</span></div>
    {source ? <>
      <p>Historical snapshot. Current build status is unknown.</p>
      <details name={archiveGroup} open>
        <summary>{source.checkpoint}</summary>
        <dl>
          <dt>Game edition</dt><dd>Exact edition unrecorded. The report includes a demo playthrough.</dd>
          <dt>Verification time</dt><dd>Unrecorded in the source report.</dd>
        </dl>
        <p>Retail promotion is on hold pending original-runtime fidelity evidence.</p>
        <ul>{acceptance.deferred_fidelity.map(gap => <li key={gap}>{gap}</li>)}</ul>
        <BuildReadmeStatus check={documentation}/>
        <details>
          <summary>Recorded checks and source</summary>
          <dl>{(Object.keys(checkLabels) as Array<keyof typeof checkLabels>).map(key =>
            <Fragment key={key}>
              <dt>{checkLabels[key]}</dt>
              <dd>{formatArchivedCheck(key)}</dd>
            </Fragment>
          )}</dl>
          <p>Source <code className="portfolio-evidence-path">{source.sourceRelativePath}</code></p>
          <p>SHA-256 <code className="portfolio-evidence-hash">{source.sourceSha256}</code></p>
        </details>
      </details>
      {source.projectId === packageReport.projectId && <details name={archiveGroup}>
        <summary>{packageReport.buildId}</summary>
        <dl>
          <dt>Game edition</dt><dd>Azrael's Tear demo reconstruction</dd>
          <dt>Verification time</dt><dd>Unrecorded in the package report.</dd>
        </dl>
        <p>The package report lists these unresolved original-runtime fidelity checks.</p>
        <ul>{packageReport.fidelityGaps.map(gap => <li key={gap}>{gap}</li>)}</ul>
        <BuildReadmeStatus check={packageDocumentation}/>
        <p>The archive includes a legacy <code>README.txt</code>.</p>
        <details>
          <summary>Reported package checks and source</summary>
          <ul>{packageReport.checks.map(check => <li key={check}>{check}</li>)}</ul>
          <p>Source <code className="portfolio-evidence-path">{packageReport.sourceRelativePath}</code></p>
          <p>SHA-256 <code className="portfolio-evidence-hash">{packageReport.sourceSha256}</code></p>
          <p>Package checksum manifest SHA-256 <code className="portfolio-evidence-hash">{packageReport.packageManifestSha256}</code></p>
        </details>
      </details>}
      {source.projectId === packageReport.projectId && <BuildCheckComparison olderBuildId={source.checkpoint}/>}
    </> : <p>No pinned build report is available for this project. Build and verification status are unknown.</p>}
  </section>;
}
