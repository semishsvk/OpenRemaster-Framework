import { useState } from "react";
import "./gate-a-styles.css";
import { gateAView, GATE_A_IDS, R18A_SOURCE, unsignedGateReviewBrief,
  type GateABundle } from "./gate-a-r18a";

/**
 * Read-only release-trust child panel.
 * Selecting an entry or downloading an UNSIGNED local brief cannot make
 * a Windows task, network call, signature, Owner lease or Native job.
 */
export default function GateAReviewPanel({evidence}:{evidence:unknown}){
  const [selected,setSelected]=useState<string>(GATE_A_IDS[0]);
  const result=gateAView(evidence);
  if(!result.data) return <section className="gatea-shell" aria-label="Gate A independent reviewer evidence">
    <div className="gatea-head">
      <div><span className="gatea-kicker">GATE A / SOURCE RECONCILIATION</span>
      <h3>Gate A evidence is unavailable</h3></div>
      <span className="gatea-pill gatea-hold">SOURCE REJECTED · HOLD</span>
    </div>
    <p className="gatea-explainer">Pinned r18a data failed strict validation. No current Owner, witness, Windows service or execution authority may be inferred.</p>
  </section>;

  const data:GateABundle=result.data;
  const current=data.gates.find(g=>g.id===selected)??data.gates[0];
  const currentWave=data.waves.find(w=>w.gate_ids.includes(current.id));
  function downloadBrief(){
    // Completely local unsigned text. No server, IPC or approval endpoint.
    const content=unsignedGateReviewBrief(data,current.id);
    const blob=new Blob([content],{type:"text/plain;charset=utf-8"});
    const objectUrl=URL.createObjectURL(blob);
    const anchor=document.createElement("a");
    anchor.href=objectUrl;
    anchor.download="OpenRemaster-UNSIGNED-GateA-"+current.id+".txt";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(objectUrl);
  }
  return <section className="gatea-shell" aria-label="Gate A independent reviewer evidence">
    <div className="gatea-head">
      <div>
        <span className="gatea-kicker">ORCHESTRATOR r18a → STUDIO r11 · READ-ONLY</span>
        <h3>Independent Owner / Witness · Gate A</h3>
        <p className="gatea-explainer">Aktuálnejší zapečatený lokálny handoff pre nezávislé overovanie. Historické údaje, nie živý Host API ani podpísaná autorita.</p>
      </div>
      <span className="gatea-pill gatea-hold">9 OPEN · NO-GO</span>
    </div>
    <div className="gatea-metrics" role="group" aria-label="Gate A evidence status summary">
      <div><strong>09</strong><span>Required external gates</span></div>
      <div><strong>22</strong><span>Independent reviewer role fields</span></div>
      <div><strong>00</strong><span>Authenticated signatures</span></div>
      <div><strong>A01</strong><span>First external trust-root step</span></div>
    </div>
    <div className="gatea-notice" role="note">Nie je pripojený externý Owner, witness ani kryptografická verifikácia. Lokálne SHA a testy neudeľujú právomoc spúšťať úlohy. A, B aj C zostávajú neschválené.</div>
    <div className="gatea-layout">
      <div className="gatea-list" role="group" aria-label="Select external evidence requirement">
        {data.gates.map(g=><button key={g.id} type="button"
          className={"gatea-item "+(g.id===current.id?"gatea-active":"")}
          onClick={()=>setSelected(g.id)}
          aria-pressed={g.id===current.id}>
          <span className="gatea-item-top"><b>{g.id.split("_").slice(0,1)}</b><span className="gatea-pill gatea-hold">MISSING</span></span>
          <strong>{g.id.substring(4).replaceAll("_"," ").toLowerCase()}</strong>
          <small>{g.required_role_aliases.length} reviewer roles · no authenticated proof</small>
        </button>)}
      </div>
      <div className="gatea-detail">
        <div className="gatea-detail-head">
          <div><span className="gatea-kicker">SELECTED REQUIREMENT · WAVE {currentWave?.wave??"—"}</span>
            <h4>{current.id.replaceAll("_"," ")}</h4></div>
          <span className="gatea-pill gatea-hold">EXTERNAL PROOF ABSENT</span>
        </div>
        <p className="gatea-description">{current.external_evidence_task}</p>
        <div className="gatea-detail-grid">
          <div>
            <h5>Required independent roles</h5>
            <ul>{current.required_role_aliases.map(x=><li key={x}>{x.replaceAll("_"," ")}</li>)}</ul>
          </div>
          <div>
            <h5>Prerequisites — not accepted</h5>
            {current.predecessors.length?
              <ul>{current.predecessors.map(x=><li key={x}>{x.replaceAll("_"," ")}</li>)}</ul>:
              <p className="gatea-small">None. Begin with a separately authorized A01 trust-root review.</p>}
          </div>
        </div>
        <div className="gatea-next">
          <b>Review action only</b>
          <p>Pripravovať verejné dôkazy môže nezávislý reviewer. Tento panel nekontroluje podpisy, nevytvára účty, nemodifikuje ACL a nemá vykonávacie API.</p>
        </div>
        <button type="button" className="gatea-export" onClick={downloadBrief}>
          Download unsigned reviewer brief ↓
        </button>
      </div>
    </div>
    <div className="gatea-wave-strip" aria-label="Review dependency order">
      {data.waves.map(w=><div key={w.wave}><span>Wave {w.wave}</span>
        <b>{w.gate_ids.map(id=>id.slice(0,3)).join(" + ")}</b></div>)}
    </div>
    <div className="gatea-footer">
      <div><b>Source</b><code>{R18A_SOURCE.ownerR18a}</code></div>
      <span>Local sealed r18a · not independently signed · no Host API calls · no retry</span>
    </div>
  </section>;
}
