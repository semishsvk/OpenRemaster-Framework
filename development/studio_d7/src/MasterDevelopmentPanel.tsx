import { modelWitnessView, type EvidenceContext } from './modelWitnessView';

const modules = [
  ["Development worker", "Unsigned Studio build recorded", "Local DEV evidence; no release authority"],
  ["Secure production worker", "On hold", "Independent identity, clean rebuild and signing chain pending"],
  ["Game Logic & Completion Assurance", "Partial implementation", "Source/model analysis; authentic gameplay replay pending"],
  ["Retail reconstruction", "Isolated candidate", "Contracts and synthetic tests; original-game behavior remains unknown"],
  ["Orchestration and resources", "Admission required", "Existing K003, project owner and Resource Governor retain control"],
];

export default function MasterDevelopmentPanel({ advisory, evidenceContext }: {
  advisory?: unknown; evidenceContext?: EvidenceContext;
} = {}) {
  const witness = modelWitnessView(advisory, evidenceContext);
  return <section className="panel" aria-labelledby="master-development-title">
    <h2 id="master-development-title">Development checkpoint</h2>
    <p><strong>Shadow evaluation · Production on hold</strong></p>
    <p>Recorded on 25 October 2026. This source snapshot is a review candidate; it is not a live worker or security monitor.</p>
    <table>
      <caption>Consolidated development status</caption>
      <thead><tr><th scope="col">Capability</th><th scope="col">Status</th><th scope="col">Evidence boundary</th></tr></thead>
      <tbody>{modules.map(([name, status, boundary]) => <tr key={name}>
        <th scope="row">{name}</th><td>{status}</td><td>{boundary}</td>
      </tr>)}</tbody>
    </table>
    <p>Release remains on hold until independent validation, release authorization and controlled signing are verified.</p>
    <section aria-labelledby="model-path-title">
      <h3 id="model-path-title">{witness.title}</h3>
      <p>{witness.detail}</p>
      {witness.steps !== null && <p>Model steps checked: {witness.steps}</p>}
      {witness.references.length > 0 && <details>
        <summary>Developer Mode · Model evidence references</summary>
        <p>Reference matching is a display consistency check. This panel does not independently verify the reported path or its provenance.</p>
        <dl>{witness.references.map(([label, value]) => <div key={label}>
          <dt>{label}</dt><dd>{value}</dd>
        </div>)}</dl>
      </details>}
    </section>
    <details><summary>Developer Mode · Evidence references</summary>
      <p>Master checkpoint v002 · GLCA-001–008 · RLR-01–09 · DEV_UNSIGNED · Existing K003 execution path</p>
      <p>Development artifacts cannot promote themselves to verified production artifacts. This panel has no dispatch, signing or publication action.</p>
    </details>
  </section>;
}
