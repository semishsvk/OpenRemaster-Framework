import DevWorkerPanel from "./DevWorkerPanel";
import MasterDevelopmentPanel from "./MasterDevelopmentPanel";
import { loadStoredJson } from "./stored-json";
import brandMark from "./assets/openremaster-mark.png";
import { validateSnapshot } from "./snapshot-validation";
import { parseSnapshotJson } from "./snapshot-json";
import CoreOrionPanel from "./CoreOrionPanel";
import CanonicalCorePanel from "./CanonicalCorePanel";
import {GROUPS,labels,groupFor,groupLinks,isLegacyRoute,type PrimaryArea} from "./ux-navigation";
import QuickNavigation from "./QuickNavigation";
import { useEffect, useMemo, useRef, useState, type ChangeEvent, type ReactNode } from "react";
import initialSnapshot from "./data/snapshot.json";
import embeddedInspector from "./data/inspector-observation.json";
import { classifyCapture, validateCapture } from "./inspector";
import nativeEvidence from "./data/runtime-readiness.json";
import { nativeStatus, REQUIRED_ADMISSION_GATES, ADMISSION_LABELS } from "./native";
import archivedCrossplane from "./data/crossplane-observation.json";
import archivedOwnerReview from "./data/owner-admission-r8.json";
import { classifyCrossplane, validateCrossplane } from "./crossplane";
import { ownerView, OWNER_GATES } from "./owner";
import securityEvidence from "./data/host-security-readiness.json";
import { hostSecurityView, RELEASE_SECURITY_GATES } from "./host-security";
import packagingEvidence from "./data/native-packaging-readiness.json";
import { packagingView, PACKAGING_BLOCKERS, BLOCKER_DESCRIPTIONS } from "./packaging";
import newNodeNotice from "./data/node-notice-status.json";
import { nodeNoticeView } from "./node-notice";
import nodeOSSignature from "../evidence/NODE_v24.19.0_WINDOWS_SIGNATURE.json";
import { nodeSignatureView } from "./node-signature";
import portableEvidence from "./data/portable-host-readiness.json";
import { portableView, PORTABLE_TEST_GROUPS } from "./portable-host";
import releaseEvidence from "./data/release-trust-review.json";
import gateAReadOnlyEvidence from "./data/gate-a-r18a.json";
import GateAReviewPanel from "./GateAReviewPanel";
import HostReplayLab from "./HostReplayLab";
import NativeBuildLab from "./NativeBuildLab";
import { trustView, renderUnsignedHandoff } from "./release-trust";
import compatEvidence from "./data/component-compatibility.json";
import { compatibilityView, evaluateWhatIf, REQUIRED_PROTOCOLS, PER_COMPONENT_MISSING, type ComponentId } from "./component-compat";
import archivedArchitecture from "./data/architecture-snapshot.json";
import { architectureView } from "./architecture";
import archivedBoundedPlan from "./data/bounded-plan-evidence.json";
import { boundedPlanView,validateBoundedPlan } from "./bounded-plan";
import NextTaskLab from "./NextTaskLab";
import archivedGameCompletion from "./data/game-completion-board.json";
import {gameCompletionView,validateGameCompletion} from "./game-completion";
import GameCompletionLab from "./GameCompletionLab";

type Maturity = "SHADOW_PASS" | "SOFTWARE_TESTED" | "HOLD" | "RESEARCH" | "UNRESOLVED" | "DESIGN" | "MISSING";
type ModuleRecord = {
  id: string; title: string; area: string; maturity: Maturity; note: string;
  checkpointStatus: string; checkpointRel: string | null; checkpointSha256: string | null;
  checkpointRead: string; sourceRel: string | null; sourceSha256: string | null;
  sourceRead: string; sourcePresent: boolean; checkpointPresent: boolean;
  testsPerPlatform: number | null; release: string; productionAdmitted: boolean;
};
type ComponentRecord = { id: string; required: boolean; launchPolicy: string; isolatedProcess: boolean; installed: boolean };
type Snapshot = {
  schema: string; generatedUtc: string; captureMethod: string; authority: string; host: string;
  production: { admission: string; dispatchAuthorized: boolean; autoRetry: boolean; ownerAuthenticated: boolean; witnessAuthenticated: boolean; trustedRuntimeConnected: boolean; servicesLiveQueried: boolean; nativeWorkerCurrentState: string; guiLeaseCurrentState: string };
  policy: { maxHeavySlots: number; singleWriter: boolean; gameAutoLightDefault: boolean; gameAutoLightRuntimeBound: boolean; originalGamesImmutable: boolean; unknownOutcome: string };
  packaging: { status: string; planSha256: string | null; plannedSetup: string; targetApp: string; approvedIconLocated: boolean; components: ComponentRecord[]; installerAccepted: boolean };
  modules: ModuleRecord[];
  projects: { id: string; type: string; runtime: string }[];
};
type Page = "overview" | "projects" | "completion" | "modules" | "inspector" | "replay" | "buildlab" | "native" | "portable" | "runtime" | "security" | "crossplane" | "architecture" | "nexttask" | "assets" | "fidelity" | "intelligence" | "governor" | "localization" | "evidence" | "components" | "compat" | "trust" | "settings";
const BASE = initialSnapshot as Snapshot;
const PINNED_ARCHITECTURE = (()=>{try{return architectureView(archivedArchitecture);}catch{return null;}})();
const NAV: { id: Page; name: string; glyph: string; group: string }[] = [
  { id: "overview", name: "Mission Control", glyph: "◫", group: "WORKSPACE" },
  { id: "projects", name: "Projects", glyph: "▦", group: "WORKSPACE" },
  { id: "completion", name: "Game Completion", glyph: "◇", group: "WORKSPACE" },
  { id: "modules", name: "Module Registry", glyph: "▤", group: "PLATFORM" },
  { id: "inspector", name: "Checkpoint Inspector", glyph: "⌕", group: "PLATFORM" },
  { id: "replay", name: "Host Replay Lab", glyph: "⊶", group: "PLATFORM" },
  { id: "buildlab", name: "Native Build Lab", glyph: "▱", group: "PLATFORM" },
  { id: "native", name: "Native IPC Lab", glyph: "⧉", group: "PLATFORM" },
  { id: "portable", name: "Portable Host", glyph: "⤳", group: "PLATFORM" },
  { id: "runtime", name: "Runtime & Packaging", glyph: "▥", group: "PLATFORM" },
  { id: "security", name: "Host Security", glyph: "⬡", group: "PLATFORM" },
  { id: "crossplane", name: "Framework ↔ ORION", glyph: "⇆", group: "PLATFORM" },
  { id: "architecture", name: "Architecture & Completion", glyph: "◇", group: "PLATFORM" },
  { id: "nexttask", name: "Next Task Lab", glyph: "↦", group: "PLATFORM" },
  { id: "assets", name: "Asset Labs", glyph: "◇", group: "PLATFORM" },
  { id: "fidelity", name: "Fidelity Gates", glyph: "◎", group: "PLATFORM" },
  { id: "intelligence", name: "ORION & Knowledge", glyph: "✦", group: "PLATFORM" },
  { id: "governor", name: "Governor", glyph: "◉", group: "PLATFORM" },
  { id: "localization", name: "Localization Lab", glyph: "文", group: "PLATFORM" },
  { id: "evidence", name: "Evidence", glyph: "≡", group: "MANAGEMENT" },
  { id: "components", name: "Component Manager", glyph: "▣", group: "MANAGEMENT" },
  { id: "compat", name: "Compatibility Lab", glyph: "⧖", group: "MANAGEMENT" },
  { id: "trust", name: "Release & Trust", glyph: "◇", group: "MANAGEMENT" },
  { id: "settings", name: "Settings", glyph: "⚙", group: "MANAGEMENT" },
];
const GATES = [
  { id: "01", title: "Oracle alignment", detail: "Same source identity, scene, camera, ticks, replay and independently reopened capture bytes." },
  { id: "02", title: "Admissibility", detail: "Comparison is permitted only when the oracle pair is aligned; blocked is not a visual failure." },
  { id: "03", title: "Causal fidelity", detail: "Hypotheses remain hypotheses until a controlled intervention supports a mechanism." },
  { id: "04", title: "Resource resolution", detail: "Validate case-insensitive paths, layering and source hashes; source order alone is not runtime proof." },
  { id: "05", title: "Semantic population", detail: "Distinguish definitions, references and instantiated game-world objects." },
];
const statusText: Record<Maturity, string> = {
  SHADOW_PASS: "SHADOW TESTED", SOFTWARE_TESTED: "SOFTWARE TESTED", HOLD: "HOLD",
  RESEARCH: "RESEARCH", UNRESOLVED: "NOT SELECTED", DESIGN: "DESIGN ONLY", MISSING: "SOURCE MISSING",
};
function stateClass(status: Maturity) {
  if (status === "SHADOW_PASS" || status === "SOFTWARE_TESTED") return "tested";
  if (status === "HOLD" || status === "MISSING") return "hold";
  return "pending";
}
function shortHash(value: string | null) { return value ? value.slice(0, 12) + "…" : "—"; }
function dateDisplay(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "unknown" : parsed.toLocaleString("sk-SK", { dateStyle: "medium", timeStyle: "short" });
}
function validateIncoming(value: unknown): value is Snapshot {
  return validateSnapshot(value, BASE);
}
function Tag({ children, kind = "muted" }: { children: ReactNode; kind?: "muted" | "hold" | "tested" | "pending" | "blue" }) {
  return <span className={"tag tag-" + kind}>{children}</span>;
}
function Panel({ title, eyebrow, children, extra, className = "" }: { title: string; eyebrow?: string; children: ReactNode; extra?: ReactNode; className?: string }) {
  return <section className={"panel " + className}><div className="panel-header"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h3>{title}</h3></div>{extra}</div>{children}</section>;
}
function ModuleBadge({ module }: { module: ModuleRecord }) {
  return <Tag kind={stateClass(module.maturity)}>{statusText[module.maturity] || "UNVERIFIED"}</Tag>;
}
function Metric({ label, value, desc, attention = false }: { label: string; value: string | number; desc: string; attention?: boolean }) {
  return <div className="metric"><span className="metric-label">{label}</span><strong className={attention ? "attention" : ""}>{value}</strong><span className="metric-desc">{desc}</span></div>;
}

export default function App() {
  const [snapshot, setSnapshot] = useState<Snapshot>(BASE);
  const [page, setPage] = useState<Page>(() => {
    const id = window.location.hash.slice(1);
    return NAV.find(n => n.id === id)?.id ?? "overview";
  });
  const [,setUxGroup] = useState<PrimaryArea>(()=>groupFor(window.location.hash.slice(1)));
  const [selected, setSelected] = useState<string>("orion");
  const [search, setSearch] = useState("");
  const [area, setArea] = useState("All");
  const [imported, setImported] = useState(false);
  const [message, setMessage] = useState("");
  const [gameDraft, setGameDraft] = useState<boolean>(BASE.policy.gameAutoLightDefault);
  const [inspector, setInspector] = useState<unknown>(embeddedInspector);
  const [clock, setClock] = useState(() => Date.now());
  const [inspectorBusy, setInspectorBusy] = useState(false);
  const [selectedCheckpoint, setSelectedCheckpoint] = useState<string | null>(null);
  const [runtimeTab, setRuntimeTab] = useState<"python"|"node">("python");
  const [gateSearch, setGateSearch] = useState("");
  const [securityArea, setSecurityArea] = useState<"all"|"identity"|"authority"|"release">("all");
  const [nativeModuleQuery, setNativeModuleQuery] = useState("");
  const [portableCaseFilter, setPortableCaseFilter] = useState<"all" | "held" | "success">("all");
  const [reviewStage, setReviewStage] = useState<"A" | "B" | "C">("A");
  const [compatFilter,setCompatFilter] = useState<"all"|"source"|"missing">("all");
  const [selectedCompat,setSelectedCompat] = useState<ComponentId>("framework_core");
  const [whatIfSources,setWhatIfSources] = useState(false);
  const [crossplane, setCrossplane] = useState<unknown>(archivedCrossplane);
  const [crossplaneBusy, setCrossplaneBusy] = useState(false);
  const [selectedCapability,setSelectedCapability] = useState("ORF-ADM-001");
  const [boundedPlan,setBoundedPlan] = useState<unknown>(archivedBoundedPlan);
  const [boundedBusy,setBoundedBusy] = useState(false);
  const [gameCompletion,setGameCompletion] = useState<unknown>(archivedGameCompletion);
  const [gameCompletionBusy,setGameCompletionBusy] = useState(false);
  const upload = useRef<HTMLInputElement>(null);
  const modules = snapshot.modules;
  const lookup = (key: string) => modules.find(m => m.id === key);
  const chosen = lookup(selected) ?? modules[0];
  const areas = ["All", ...new Set(modules.map(m => m.area))];
  const filtered = useMemo(() => modules.filter(m =>
    (area === "All" || m.area === area) &&
    (m.title + " " + m.note + " " + m.id).toLocaleLowerCase("sk").includes(search.toLocaleLowerCase("sk"))
  ), [modules, area, search]);
  const sourceCount = modules.filter(m => m.sourcePresent).length;
  const testCount = new Set(modules.filter(m => m.testsPerPlatform !== null && m.checkpointSha256).map(m => m.checkpointSha256)).size;
  const navInfo = NAV.find(n => n.id === page)!;
  const currentUxGroup = groupFor(page);
  const gameCompletionState=gameCompletionView(gameCompletion);
  const architecture = PINNED_ARCHITECTURE;
  const selectedCapabilityInfo = architecture?.capabilities.find(c=>c.id===selectedCapability)??architecture?.capabilities[0];
  const boundedView = boundedPlanView(boundedPlan);
  const compView=compatibilityView(compatEvidence);
  const comp=compView.data;
  const activeComp=comp?.components.find(c=>c.id===selectedCompat) ?? comp?.components[0];
  const listedComp=(comp?.components??[]).filter(c=>compatFilter==="all" || (compatFilter==="source"?c.historicalSourcePresent:!c.historicalSourcePresent));
  const dryComponent=comp?evaluateWhatIf(comp,whatIfSources):null;
  const releaseTrust = trustView(releaseEvidence);
  const trustData = releaseTrust.review;
  const stageSelected = trustData?.sequentialStages.find(s=>s.id===reviewStage);
  const portableModel = portableView(portableEvidence);
  const portableData = portableModel.data;
  const portableCases = (portableData?.transport.testCases ?? []).filter(c => portableCaseFilter==="all" || (portableCaseFilter==="success"?c.mode==="success":c.mode!=="success"));
  const matchedNodeNotice = nodeNoticeView(newNodeNotice);
  const nodeWindowsSignature = nodeSignatureView(nodeOSSignature).data;
  const nodeNoticeData = matchedNodeNotice.data;
  const runtimeEvidenceView = packagingView(packagingEvidence);
  const runtimeInfo = runtimeEvidenceView.data;
  const filteredNativeModules = (runtimeInfo?.loadedModuleAudit.moduleFileNamesAndHashes ?? []).filter(m => m.fileName.toLowerCase().includes(nativeModuleQuery.toLowerCase()));
  const securityView = hostSecurityView(securityEvidence);
  const securityData = securityView.data;
  const displayedSecurityGates = RELEASE_SECURITY_GATES.filter(g => securityArea === "all" || g.role === securityArea);
  const crossplaneView = classifyCrossplane(crossplane, clock);
  const crossplaneData = crossplaneView.data;
  const ownerReview = ownerView(archivedOwnerReview);
  const ipc = nativeStatus(nativeEvidence);
  const auditedRuntime = ipc.report?.binaryClosure.binaries[runtimeTab];
  const missingAdmissionGates = REQUIRED_ADMISSION_GATES.filter(k => ADMISSION_LABELS[k].toLocaleLowerCase("sk").includes(gateSearch.toLocaleLowerCase("sk")));
  const inspectorView = classifyCapture(inspector, clock);
  const inspectorData = inspectorView.capture;
  const inspectorRows = inspectorData?.records ?? [];
  const inspectorSelected = inspectorRows.find(r => r.id === selectedCheckpoint) ?? inspectorRows[0];
  useEffect(() => {setUxGroup(currentUxGroup);}, [currentUxGroup]);
  useEffect(() => { const id = window.setInterval(() => setClock(Date.now()), 1000); return () => window.clearInterval(id); }, []);
  useEffect(() => { const changed = () => { const hash = window.location.hash.slice(1); const entry = NAV.find(n => n.id === hash); if (entry) setPage(entry.id); else {window.history.replaceState(null,'','#overview');setPage('overview');} }; window.addEventListener("hashchange", changed); return () => window.removeEventListener("hashchange", changed); }, []);
  useEffect(() => { if (window.location.hash !== "#" + page) {if(!isLegacyRoute(window.location.hash.slice(1)))window.history.replaceState(null,'','#'+page);else window.location.hash=page;} }, [page]);

  function inspect(id: string) { setSelected(id); setPage("modules"); setSearch(""); setArea("All"); }
  async function reloadInspectorCapture() {
    setInspectorBusy(true);
    setInspector(null); // Fail closed: never retain an earlier view on transport failure.
    setSelectedCheckpoint(null);
    try {
      const received: unknown = await loadStoredJson("inspector");
      if (!validateCapture(received)) throw Error("CAPTURE_CONTRACT_REJECTED");
      setInspector(received);
      setClock(Date.now());
      setMessage("Stored Inspector capture loaded. This action did not invoke the Host or refresh the source observation.");
    } catch { setInspector(null); setMessage("Inspector capture unavailable or rejected. No previous rows retained; production remains HOLD."); }
    finally { setInspectorBusy(false); }
  }
  async function reloadGameCompletion() {
    setGameCompletionBusy(true);
    setGameCompletion(null);
    try {
      const parsed: unknown = await loadStoredJson("completion");
      if(!validateGameCompletion(parsed)) throw Error("ORIGINAL_GAME_SOURCE_PROJECTION_INVALID");
      setGameCompletion(parsed);
      setMessage("Archived game blocker evidence reloaded. No original runtime, K003, model or worker was executed.");
    } catch {
      setGameCompletion(null);
      setMessage("Game source evidence missing or changed: previous results cleared. Production remains HOLD.");
    } finally {setGameCompletionBusy(false);}
  }
  async function reloadBoundedPlanEvidence() {
    setBoundedBusy(true);
    setBoundedPlan(null); // clear old state before every read (no stale promotion)
    try {
      const parsed: unknown = await loadStoredJson("plan");
      if(!validateBoundedPlan(parsed)) throw Error("BOUND_PLAN_CONTRACT_REJECTED");
      setBoundedPlan(parsed);
      setMessage("Historical read-only bounded plan reloaded; no model, K003, worker or Owner was called.");
    } catch {
      setBoundedPlan(null);
      setMessage("Archived plan rejected or missing; previous proposal cleared, authority remains HOLD.");
    } finally {setBoundedBusy(false);}
  }
  async function reloadCrossplaneCapture() {
    setCrossplaneBusy(true);
    setCrossplane(null);
    try {
      const data: unknown = await loadStoredJson("crossplane");
      if(!validateCrossplane(data)) throw Error("CROSSPLANE_CONTRACT_REJECTED");
      setCrossplane(data);setClock(Date.now());
      setMessage("Historic source-bound ORION snapshot reloaded. No new CLI, model, Native Worker or K003 execution.");
    } catch {setCrossplane(null);setMessage("Crossplane record rejected or unavailable; previous data cleared, authority remains HOLD.");}
    finally{setCrossplaneBusy(false);}
  }
  async function onImport(e: ChangeEvent<HTMLInputElement>) {
    const file = e.currentTarget.files?.[0];
    e.currentTarget.value = "";
    if (!file) return;
    if (file.size > 1_048_576) { setMessage("Snapshot rejected: size exceeds 1 MiB."); return; }
    try {
      const parsed: unknown = parseSnapshotJson(new TextDecoder('utf-8', {fatal:true}).decode(await file.arrayBuffer()));
      if (!validateIncoming(parsed)) { setMessage("Snapshot rejected: schema or fail-closed policy mismatch."); return; }
      setSnapshot(parsed); setImported(true); setMessage("Local snapshot imported. Contents are untrusted and never grant authority.");
    } catch { setMessage("Snapshot rejected: invalid JSON."); }
  }
  function exportNativeReport() {
    if (!ipc.report) return;
    const blob = new Blob([JSON.stringify(ipc.report, null, 2)], { type:"application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "orf-ui004-local-runtime-readiness.json"; a.click(); URL.revokeObjectURL(url);
  }
  function downloadReviewBrief() {
    if (!trustData || !stageSelected) return;
    const brief = renderUnsignedHandoff(trustData,reviewStage);
    const url = URL.createObjectURL(new Blob([brief],{type:"text/plain;charset=utf-8"}));
    const link = document.createElement("a");
    link.href=url;
    link.download="OpenRemaster-UNSIGNED-review-stage-"+reviewStage+".txt";
    link.click();
    URL.revokeObjectURL(url);
    setMessage("An unsigned read-only reviewer brief was prepared locally. Nothing was submitted or approved.");
  }
  function exportSnapshot() {
    const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "openremaster-studio-shadow-snapshot.json"; a.click();
    URL.revokeObjectURL(url);
  }

  function smallModule(id: string) {
    const m = lookup(id);
    if (!m) return null;
    return <div className="module-mini" key={id}><span className="module-symbol">◇</span><div className="grow"><strong>{m.title}</strong><small>{m.note}</small></div><button className="text-action" onClick={() => inspect(id)}>Inspect ↗</button></div>;
  }

  return <div className="app-shell">
    <a className="skip-link" href="#studio-content" onClick={event=>{event.preventDefault();document.getElementById('studio-content')?.focus();}}>Skip to main content</a>
    <aside className="sidebar">
      <div className="brand" aria-label="OpenRemaster Studio"><img className="brand-mark" src={brandMark} alt="" width={40} height={40}/><div className="brand-wordmark"><div className="brand-name">OpenRemaster</div><div className="brand-sub">STUDIO</div></div></div>
      <div className="workspace-pill"><span className="pulse-dot" /><div><b>Local workspace</b><small>Read-only / uncommissioned</small></div></div>
      <nav aria-label="Studio primary navigation">
        {GROUPS.map(group => <button key={group} type="button" className={"nav-item "+(currentUxGroup===group?"active":"")} aria-current={currentUxGroup===group?"page":undefined} onClick={()=>{setUxGroup(group);const first=groupLinks(group)[0];if(isLegacyRoute(first))setPage(first as Page);}}>{labels[group]}</button>)}
      </nav>
      <nav aria-label="Studio section navigation">
        <div className="sidebar-group">{labels[currentUxGroup]} · tools</div>
        {NAV.filter(item=>(groupLinks(currentUxGroup) as readonly string[]).includes(item.id)).map(item=><button key={item.id} type="button" className={"nav-item "+(page===item.id?"active":"")} onClick={()=>setPage(item.id)} aria-current={page===item.id?"page":undefined}><span className="nav-symbol" aria-hidden="true">{item.glyph}</span>{item.name}</button>)}
      </nav>
      <nav aria-label="Studio global navigation">
        <button type="button" className={"nav-item "+(page==="settings"?"active":"")} onClick={()=>setPage("settings")}>Settings</button>
      </nav>
      <QuickNavigation items={NAV} onNavigate={id=>{if(isLegacyRoute(id))setPage(id as Page);}} />
      <div className="sidebar-footer"><div className="sidebar-rule"/><div className="small-row"><span>System authority</span><b className="red">HOLD</b></div><div className="small-row"><span>Live dispatch</span><b>DISABLED</b></div><small>UI-015 · r14 · Native Build evidence</small></div>
    </aside>

    <div className="main-shell">
      <header className="topbar">
        <div className="breadcrumb">PLATFORM <span>/</span> <strong>{navInfo.name}</strong></div>
        <div className="header-actions">
          <Tag kind="hold">PRODUCTION HOLD</Tag>
          {imported && <span data-testid="import-provenance"><Tag kind="pending">IMPORTED SNAPSHOT · UNTRUSTED DISPLAY DATA</Tag></span>}
          <div className="header-separator" />
          <span className="snapshot-time" title={`Historical source observation; not current host inventory · ${snapshot.generatedUtc}`}>HISTORICAL SNAPSHOT · {dateDisplay(snapshot.generatedUtc)}</span>
          <input className="visually-hidden" ref={upload} id="import-snapshot" type="file" accept=".json,application/json" onChange={onImport}/>
          <button className="top-button" onClick={() => upload.current?.click()}>Import snapshot</button>
        </div>
      </header>
      <main className="main-content" id="studio-content" tabIndex={-1}>
        {message && <div className="notice" role="status"><span>{message}</span><button onClick={() => setMessage("")} aria-label="Dismiss">×</button></div>}
        {page === "overview" && <>
          <MasterDevelopmentPanel />
          <div className="page-intro"><div className="eyebrow">OPENREMASTER / MISSION CONTROL</div><h1>Platform overview<span className="title-dot">.</span></h1><p>Jednotný pohľad na pripravené moduly, dôkazy a produkčné brány. Žiadna činnosť tejto konzoly nespúšťa herné procesy, workerov ani K003.</p></div>
          <section className="ux-action-panel" aria-label="Next actions">
            <div className="eyebrow">NEXT ACTIONS · HISTORICAL SOURCE ONLY</div>
            <h2>Continue safely</h2>
            <p>Read-only evidence is available. No current Owner lease, live job status, or verified resume checkpoint has been established.</p>
            <div className="ux-action-grid">
              <div><strong>Needs attention</strong><p>Production admission is blocked until independent Owner/Witness and Windows trust gates pass.</p><button type="button" className="secondary-button" onClick={()=>setPage("trust")}>Review blockers →</button></div>
              <div><strong>Explore projects</strong><p>Review project source status without claiming current runtime execution.</p><button type="button" className="secondary-button" onClick={()=>setPage("projects")}>Open projects →</button></div>
              <div><strong>Plan the next task</strong><p>Inspect bounded historical plans; no worker is launched from this view.</p><button type="button" className="secondary-button" onClick={()=>setPage("nexttask")}>View plan →</button></div>
            </div>
          </section>
          <div className="hero-card"><div><div className="hero-eyebrow"><span className="pulse-dot red-bg" /> CONTROL PLANE STATUS</div><h2>Built to integrate.<br/><span>Not authorized to execute.</span></h2><p>Vývojové zdroje sú dostupné, ale nezávislá autorita Owner/Witness, Windows identity a produkčné prijatie zostávajú neoverené.</p><button className="hero-link" onClick={() => setPage("trust")}>Review release readiness <span>↗</span></button></div><div className="hero-status"><span>RUNTIME GATE</span><b>HOLD</b><small>NO AUTO RETRY</small><i>00</i></div></div>
          <div className="metric-grid"><Metric label="Tracked modules" value={modules.length} desc="Allowlisted source records"/><Metric label="Source pins" value={sourceCount + " / " + modules.length} desc="Local SHA-256 only"/><Metric label="Reported test suites" value={testCount} desc="Distinct checkpoint sources"/><Metric label="Authorized jobs" value="0" desc="Dispatch unavailable" attention /></div>
          <div className="two-col"><Panel eyebrow="ARCHITECTURE" title="Runtime boundaries" extra={<Tag kind="blue">SINGLE-WRITER</Tag>}>
            <div className="pipeline"><div className="pipeline-step"><span>01</span><div><b>Studio UI</b><small>Evidence projection · no executors</small></div></div><div className="pipe-line"/><div className="pipeline-step"><span>02</span><div><b>Inspector Host</b><small>Read-only health & checkpoints; isolated candidate</small></div></div><div className="pipe-line"/><div className="pipeline-step faded"><span>03</span><div><b>Core → K003 → Owner/Witness</b><small>Trust boundary not admitted · no dispatch</small></div><Tag kind="hold">BLOCKED</Tag></div></div>
            </Panel><Panel eyebrow="AVAILABLE EVIDENCE" title="Integrated source modules" extra={<button className="text-action" onClick={() => setPage("modules")}>View all ↗</button>}>
              <div className="mini-list">{["host_api","inspector_controller","native_dependencies","native_loads","orion_studio_bridge","orion","governor","fidelity_evidence","localization_lab"].map(smallModule)}</div>
            </Panel></div>
          <Panel eyebrow="WHAT IS REAL" title="Readiness is not authorization"><div className="three-notes"><div><b>Software tested</b><p>Lokálne verifikované izolované implementácie a checkpointy.</p></div><div><b>Runtime disconnected</b><p>Žiadne aktuálne owner leases, služby ani GPU vykonávanie sa z UI neoverovali.</p></div><div><b>Fail-closed</b><p>Unknown outcome → HOLD_NO_AUTO_RETRY. Žiadne tiché povýšenie na PASS.</p></div></div></Panel>
        </>}
        {page === "modules" && <>
          <div className="page-intro"><div className="eyebrow">PLATFORM / REGISTRY</div><h1>Module Registry<span className="title-dot">.</span></h1><p>Konkrétne zdrojové a checkpointové väzby. Zelený status označuje izolované testy, nie produkčnú autorizáciu.</p></div>
          <div className="registry-controls"><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search modules, source files and capabilities…" aria-label="Search modules"/><select value={area} onChange={e => setArea(e.target.value)} aria-label="Filter by area">{areas.map(a => <option key={a} value={a}>{a}</option>)}</select><span>{filtered.length} RECORDS</span></div>
          <div className="registry-layout"><div className="registry-list">{filtered.map(m => <button key={m.id} className={"registry-record " + (chosen?.id === m.id ? "selected" : "")} onClick={() => setSelected(m.id)}><div className="record-row"><strong>{m.title}</strong><span>↗</span></div><div className="record-description">{m.note}</div><div className="record-foot"><ModuleBadge module={m}/><span className="mono-muted">{m.testsPerPlatform === null ? "NO TEST COUNT" : m.testsPerPlatform + " TESTS REPORTED"}</span></div></button>)}{filtered.length === 0 && <p className="empty">No matching records.</p>}</div>
          {chosen && <Panel eyebrow={"MODULE / " + chosen.id.toUpperCase()} title={chosen.title} className="detail-panel"><div className="detail-state"><ModuleBadge module={chosen}/><Tag kind="hold">PRODUCTION NOT ADMITTED</Tag></div><p className="detail-note">{chosen.note}</p>
            <div className="detail-section"><label>CHECKPOINT ASSERTION</label><p className="break-any">{chosen.checkpointStatus}</p></div>
            <div className="detail-section"><label>CHECKPOINT FILE · LOCAL SHA</label><p className="source-path">{chosen.checkpointRel || "Not selected"}</p><code>{chosen.checkpointSha256 || chosen.checkpointRead}</code></div>
            <div className="detail-section"><label>PINNED SOURCE · LOCAL SHA</label><p className="source-path">{chosen.sourceRel || "Not selected"}</p><code>{chosen.sourceSha256 || chosen.sourceRead}</code></div>
            <div className="detail-section"><label>SOFTWARE TEST EVIDENCE</label><strong>{chosen.testsPerPlatform === null ? "Not available in selected checkpoint" : chosen.testsPerPlatform + " reported software tests (platform/scope varies)"}</strong><small>Reported values are not rerun by Studio; SHA-256 is not an independent signature.</small></div></Panel>}
          </div>
        </>}
        {page === "buildlab" && <DevWorkerPanel/>}
        {page === "buildlab" && <NativeBuildLab onHostReplay={()=>setPage("replay")}
          onCompatibility={()=>setPage("compat")} onTrust={()=>setPage("trust")}/>}
        {page === "replay" && <HostReplayLab
          onTrust={()=>setPage("trust")} onInspector={()=>setPage("inspector")}
          onCompatibility={()=>setPage("compat")} onNativeBuild={()=>setPage("buildlab")}/>}
        {page === "inspector" && <>
          <div className="page-intro">
            <div className="eyebrow">PLATFORM / INSPECTOR HOST</div><h1>Checkpoint Inspector<span className="title-dot">.</span></h1>
            <p>Skutočná odpoveď existujúceho Windows Job-bound Inspector Host r1. Zobrazuje iba dva zdrojovo pripnuté frameworkové checkpointy, nie kompletný globálny register. Žiadne UI tlačidlo nespúšťa Host, K003 ani worker.</p>
          </div>
          <div className="section-banner">
            <Tag kind={inspectorView.phase === "RECENT_READONLY" ? "blue" : "hold"}>{inspectorView.phase === "RECENT_READONLY" ? "RECENT READ-ONLY" : inspectorView.phase === "HISTORICAL_ONLY" ? "EXPIRED / ARCHIVE" : "HOLD / NO OBSERVATION"}</Tag>
            <span>Independent owner: NOT ADMITTED · Production: HOLD · {inspectorView.code}</span>
            <button className="top-button" disabled={inspectorBusy} onClick={reloadInspectorCapture}>{inspectorBusy ? "Loading…" : "Reload saved capture"}</button>
          </div>
          <div className="metric-grid">
            <Metric label="Pinned checkpoints" value={inspectorRows.length} desc="Scope limited to read-only registry" />
            <Metric label="Host RPC receipts" value={inspectorData?.requestAudit.length ?? 0} desc="Validated one-shot method responses" />
            <Metric label="Current observations" value={inspectorView.activeCount} desc="30-second observation lifetime" />
            <Metric label="Owner admission" value="HOLD" desc="Local file hashes are not signatures" attention />
          </div>
          {inspectorView.phase === "HOLD" && <div className="soft-warning">Valid Inspector capture is not available. Existing results have been cleared, not silently reused. Capture status: {inspectorView.code}.</div>}
          {inspectorView.phase === "HISTORICAL_ONLY" && <div className="soft-warning">These records are archived source evidence only. The 30-second observation freshness window expired, and current live status is unknown. No automatic retry is performed.</div>}
          {inspectorView.phase === "RECENT_READONLY" && <div className="inspector-note">Recent source-bound observation; remains production HOLD and never proves that these are the latest global checkpoints.</div>}
          <div className="two-col">
            <Panel eyebrow="PINNED CHECKPOINT SCOPE" title="Source reports" extra={<Tag kind="pending">NOT GLOBAL REGISTRY</Tag>}>
              {inspectorRows.length ? <div className="checkpoint-list">
                {inspectorRows.map(r => <button key={r.id} onClick={() => setSelectedCheckpoint(r.id)} className={"checkpoint-record " + (inspectorSelected?.id === r.id ? "selected" : "")}>
                  <div className="checkpoint-row"><strong>{r.workstream}</strong><span>›</span></div>
                  <div className="source-path">{r.id}</div>
                  <p>{r.reportedStatus}</p>
                  <Tag kind={inspectorView.phase === "RECENT_READONLY" ? "blue" : "pending"}>{inspectorView.phase === "RECENT_READONLY" ? "OBSERVED READ-ONLY" : "ARCHIVED REPORT"}</Tag>
                </button>)}
              </div> : <p className="empty">No valid checkpoint records to display.</p>}
            </Panel>
            <Panel eyebrow="CHECKPOINT PROVENANCE" title={inspectorSelected?.workstream ?? "No selection"}>
              {inspectorSelected ? <>
                <div className="detail-state"><Tag kind="hold">NOT OWNER SIGNOFF</Tag><Tag kind="blue">SOURCE SHA-256</Tag></div>
                <div className="detail-section"><label>REPORTED STATUS (SOURCE CLAIM, NOT ACCEPTANCE)</label><p className="break-any">{inspectorSelected.reportedStatus}</p></div>
                <div className="detail-section"><label>PROJECT / SCOPE</label><strong>{inspectorSelected.project} · {inspectorSelected.scope}</strong></div>
                <div className="detail-section"><label>CANONICAL SOURCE HASH</label><code>{inspectorSelected.sourceSha256}</code></div>
                <div className="detail-section"><label>SOURCE CONTRACT</label><p className="source-path">{inspectorSelected.sourceSchema}</p></div>
                <div className="detail-section"><label>UPSTREAM PARENT REFERENCES</label><p className="source-path">{inspectorSelected.parentIds.length ? inspectorSelected.parentIds.join(", ") : "No parents declared"}</p></div>
              </> : <p className="empty">The view remains empty until a bounded observation passes validation.</p>}
            </Panel>
          </div>
          <Panel eyebrow="OPERATOR-OWNED OFFLINE CAPTURE" title="Host integration contract">
            <div className="three-notes">
              <div><b>One-shot stdio</b><p>Allowed methods: health.get, checkpoints.list, checkpoints.get. The Host itself has no listener.</p></div>
              <div><b>Manual recapture</b><p>Use the fixed command below on HomePC, then click “Reload saved capture”. The browser only reads the saved JSON.</p></div>
              <div><b>No authority transfer</b><p>Host's local Job containment and SHA pins do not establish an independent Owner, Witness, publisher or live runtime lease.</p></div>
            </div>
            <div className="capture-command"><code>node tools\capture_inspector.cjs</code><span>Run from StudioUI-20261018-r2</span></div>
            <div className="source-path inspector-meta">
              <span>Captured: {inspectorData?.captureStartedUtc ? dateDisplay(inspectorData.captureStartedUtc) : "—"}</span>
              <span>Expires: {inspectorData?.expiresUtc ? dateDisplay(inspectorData.expiresUtc) : "—"}</span>
              <span>Snapshot: {inspectorData?.snapshot ?? "—"}</span>
            </div>
          </Panel>
        </>}
        {page === "portable" && <>
          <div className="page-intro">
            <div className="eyebrow">PLATFORM / HOST INTEGRATION RESEARCH</div>
            <h1>Portable Host<span className="title-dot">.</span></h1>
            <p>Skutočné zdrojovo overené NW025-AC a NW025-AD. Prenosný Node/Python Host je overený v izolovanom offline prostredí; reťazec Windows Job → Node bridge → Python používal iba syntetickú službu. Studio zatiaľ nepripája produkčný Inspector Host.</p>
          </div>
          <div className="section-banner"><Tag kind="hold">PRODUCTION HOLD</Tag>
            <span>Signed Owner/Witness, live Inspector RPC, clean-machine acceptance and native Tauri build not admitted.</span>
            <button className="top-button" onClick={()=>setPage("runtime")}>Runtime evidence ↗</button>
          </div>
          {portableData ? <>
            <div className="metric-grid">
              <Metric label="AC · historical regressions" value={portableData.host.originalRegressionCount} desc="118 Python + 70 Node, separately source verified"/>
              <Metric label="AD · Windows synthetic cases" value={portableData.transport.passed+"/7"} desc="Real OS process chain, synthetic service"/>
              <Metric label="Files rehashed today" value={portableData.host.runtimeManifestFilesReadOnlyRehashed} desc="759 source files · zero files copied"/>
              <Metric label="Production Host admission" value="HOLD" desc="No independent Owner or live RPC" attention/>
            </div>
            <div className="hero-card hero-short portable-hero"><div>
              <div className="hero-eyebrow">FROZEN NW025-AC / NW025-AD</div>
              <h2>Portable paths tested.<br/><span>Live service authorization withheld.</span></h2>
              <p>Root-relative Python + Node binaries, 849 AC source pins and verified OS job containment in 7 bounded synthetic transport scenarios. No second scheduler, no global lease and no new Studio process launcher.</p>
            </div><div className="hero-status"><span>ORIGINAL HOST</span><b>HOLD</b><small>LOCAL UNSIGNED SOURCE</small></div></div>

            <div className="two-col">
              <Panel eyebrow="NW025-AC / VERIFIED OFFLINE" title="Runtime payload boundary" extra={<Tag kind="tested">188 TESTS REPORTED</Tag>}>
                <div className="portable-chain">
                  <div><span>01</span><b>Host bootstrap</b><small>Root-relative path selection</small></div>
                  <div><span>02</span><b>Runtime manifests</b><small>Immutable SHA pins / no PATH fallback</small></div>
                  <div><span>03</span><b>Node and Python</b><small>Offline test-only execution</small></div>
                </div>
                <div className="settings-line"><b>Runtime files in original candidate</b><strong>{portableData.host.runtimeManifestFiles}</strong></div>
                <div className="settings-line"><b>Python files</b><strong>{portableData.host.pythonRuntimeFiles}</strong></div>
                <div className="settings-line"><b>Node files</b><strong>{portableData.host.nodeRuntimeFiles} (node.exe + LICENSE)</strong></div>
                <div className="settings-line"><b>Bytes rehashed read-only</b><strong>{portableData.host.runtimeManifestBytesReadOnlyRehashed.toLocaleString("sk-SK")}</strong></div>
                <div className="settings-line"><b>Missing/tampered preflight</b><Tag kind="tested">7/7 HELD</Tag></div>
                <div className="settings-line"><b>Empty-executable cases</b><Tag kind="tested">2/2 HELD</Tag></div>
                <div className="settings-line"><b>Current live Host RPC</b><Tag kind="hold">NOT EXECUTED</Tag></div>
                <div className="soft-warning">Full 188-test regression belongs to the earlier NW025-AC build, not this Studio UI test run. This continuation independently rehashed 759 present runtime files and revalidated the sealed AC/AD evidence, without launching that Host.</div>
              </Panel>
              <Panel eyebrow="NW025-AD / WINDOWS JOB-BOUND" title="Synthetic transport acceptance" extra={<Tag kind="tested">7/7 HISTORIC PASS</Tag>}>
                <div className="portable-chain">
                  <div><span>01</span><b>Windows Job owner</b><small>Suspended then assigned</small></div>
                  <div><span>02</span><b>Node bridge</b><small>Fixed, bound executable</small></div>
                  <div><span>03</span><b>Python test service</b><small>Synthetic fixture only</small></div>
                </div>
                <div className="settings-line"><b>Process cap in evidence</b><strong>{portableData.transport.testProcessCap}</strong></div>
                <div className="settings-line"><b>Kill-on-close configured</b><Tag kind="tested">YES</Tag></div>
                <div className="settings-line"><b>All recorded test processes stopped</b><Tag kind="tested">YES</Tag></div>
                <div className="settings-line"><b>Actual production Host calls</b><Tag kind="hold">0</Tag></div>
                <div className="settings-line"><b>Clean-machine validation</b><Tag kind="hold">NOT TESTED</Tag></div>
                <div className="soft-warning">This proof ran a real bounded Node → Python process chain on Windows, but the Python service was deliberately synthetic. It does not prove authentic Inspector queries, production Owner authority or source-profile admission.</div>
              </Panel>
            </div>
            <Panel eyebrow="FROZEN AC REGRESSION SUITES" title="188 test coverage by original suite" extra={<Tag kind="blue">HISTORICAL · SHA-PINNED</Tag>}>
              <div className="portable-suite-grid">{PORTABLE_TEST_GROUPS.map(g=>
                <div className="portable-suite" key={g.name}><div><strong>{g.name.replaceAll("_"," ")}</strong><span>{g.tests} tests</span></div>
                  <div className="portable-suite-track"><div style={{width:((g.tests/31)*100).toFixed(1)+"%"}}/></div>
                </div>)}</div>
            </Panel>
            <Panel eyebrow="WINDOWS SYNTHETIC TRANSPORT / NEGATIVE-FIRST" title="Seven Job-bound cases" extra={<Tag kind="hold">NO REAL SERVICE RPC</Tag>}>
              <div className="security-filter">
                {(["all","success","held"] as const).map(key=>
                  <button key={key} className={portableCaseFilter===key?"active":""} aria-pressed={portableCaseFilter===key} onClick={()=>setPortableCaseFilter(key)}>
                    {key==="all"?"All seven":key==="success"?"Success fixture":"Negative / HOLD"}
                  </button>)}
              </div>
              <div className="portable-case-grid">{portableCases.map((c,i)=>
                <div className="portable-case" key={c.mode}>
                  <span>{String(i+1).padStart(2,"0")}</span><div><strong>{c.mode.replaceAll("_"," ")}</strong><small>{c.status.replaceAll("_"," ")} · bounded test process stopped</small></div>
                  <Tag kind={c.mode==="success"?"tested":"hold"}>{c.mode==="success"?"PASS":"EXPECTED HOLD"}</Tag>
                </div>)}</div>
            </Panel>
            <div className="two-col">
              <Panel eyebrow="MINIMAL NODE ROLE" title="Proposed shipping subset" extra={<Tag kind="pending">NOT ADMITTED</Tag>}>
                <div className="settings-line"><b>runtime/node/node.exe</b><Tag kind="blue">SHA PINNED</Tag></div>
                <div className="settings-line"><b>runtime/node/LICENSE</b><Tag kind="blue">VERIFIED LICENSE</Tag></div>
                <div className="settings-line"><b>npm, npx, Corepack</b><strong>NOT PROPOSED</strong></div>
                <div className="settings-line"><b>Python runtime</b><strong>757 CONSERVATIVE FILES</strong></div>
                <div className="soft-warning">Node built-ins and a local consumer are sufficient for the reviewed bridge's offline tests. This is not a minimal Python shipping proof, full Node/npm third-party notice audit or legal redistribution authorization.</div>
                <button className="secondary-button" onClick={()=>setPage("runtime")}>Inspect Node LICENSE and DLL evidence →</button>
              </Panel>
              <Panel eyebrow="TRUSTED DEPLOYMENT EXIT CRITERIA" title="What remains blocked" extra={<Tag kind="hold">NO-GO</Tag>}>
                <div className="settings-line"><b>Real Inspector portability</b><Tag kind="hold">NOT TESTED</Tag></div>
                <div className="settings-line"><b>Separate clean Windows machine</b><Tag kind="hold">NOT TESTED</Tag></div>
                <div className="settings-line"><b>Full OS DLL loader closure</b><Tag kind="hold">UNVERIFIED</Tag></div>
                <div className="settings-line"><b>Independent Owner / Witness</b><Tag kind="hold">UNSIGNED</Tag></div>
                <div className="settings-line"><b>Native Tauri 2 Studio application</b><Tag kind="hold">NOT BUILT</Tag></div>
                <div className="settings-line"><b>Existing approved Studio icon</b><Tag kind="pending">FILE NOT VERIFIED</Tag></div>
                <div className="mini-list">{["portable_host_bindings","portable_host_transport"].map(smallModule)}</div>
              </Panel>
            </div>
            <Panel eyebrow="LOCAL CRYPTOGRAPHIC PROVENANCE" title="Pinned source references" extra={<Tag kind="blue">NOT OWNER SIGNATURE</Tag>}>
              <div className="crossplane-hashes">{Object.entries(portableData.sourcePins).map(([role,sha])=>
                <div key={role}><strong>{role}</strong><code>{sha}</code></div>)}</div>
              <p className="native-module-note">Historical AC/AD outcomes are source-grounded and verified as immutable local evidence. The current Studio browser performs no source execution, no worker launch and no independent security authority election.</p>
            </Panel>
          </> : <div className="soft-warning">Portable Host source evidence did not pass the strict HOLD projection ({portableModel.code}). No tests or portability status will be presented as accepted.</div>}
        </>}
        {page === "runtime" && <>
          <div className="page-intro">
            <div className="eyebrow">PLATFORM / DEPLOYMENT EVIDENCE</div>
            <h1>Runtime & Packaging<span className="title-dot">.</span></h1>
            <p>Zdrojovo overené audity NW025-U a NW025-Z. Statický graf a skutočné načítanie DLL sú <strong>dve samostatné výskumné overenia</strong>, nie kompletná produkčná závislostná uzávierka ani inštalačný manifest.</p>
          </div>
          <div className="section-banner"><Tag kind="hold">INSTALLER NO-GO</Tag>
            <span>Complete DLL closure, redistribution rights, trusted Owner/Witness and Tauri installer remain unverified · {runtimeEvidenceView.phase}</span>
            <button className="top-button" onClick={()=>setPage("components")}>Component plan ↗</button>
          </div>
          {runtimeInfo ? <>
            <div className="metric-grid">
              <Metric label="Direct Windows import names" value={runtimeInfo.staticAudit.directExternalNames} desc="37 original runtime binaries · NW025-U"/>
              <Metric label="Static graph visited" value={runtimeInfo.staticAudit.boundedGraphFiles} desc="Budget reached · no closure proof"/>
              <Metric label="Observed loaded modules" value={runtimeInfo.loadedModuleAudit.observedNativeModules} desc="NW025-Z · one scoped Windows snapshot"/>
              <Metric label="Installer acceptance" value="NO-GO" desc="Unsigned, incomplete runtime closure" attention/>
            </div>
            <div className="two-col">
              <Panel eyebrow="NW025-U · STATIC DEPENDENCY AUDIT" title="Direct imports & bounded graph" extra={<Tag kind="pending">PARTIAL</Tag>}>
                <div className="native-release-metrics">
                  <div><strong>{runtimeInfo.staticAudit.directSystem32FilenameCandidates}</strong><span>System32 filename candidates</span></div>
                  <div><strong>{runtimeInfo.staticAudit.directApiSetContracts}</strong><span>Windows API-set contracts</span></div>
                  <div><strong>{runtimeInfo.staticAudit.directUnclassified}</strong><span>Unclassified direct names</span></div>
                </div>
                <div className="settings-line"><b>Runtime root files examined</b><strong>{runtimeInfo.staticAudit.originalBinaryRootCount}</strong></div>
                <div className="settings-line"><b>Graph traversal limit</b><Tag kind="pending">256 FILES / STOPPED</Tag></div>
                <div className="settings-line"><b>Windows files visited</b><strong>{runtimeInfo.staticAudit.boundedGraphWindowsFiles}</strong></div>
                <div className="settings-line"><b>Observed static import edges</b><strong>{runtimeInfo.staticAudit.boundedGraphImportEdges.toLocaleString("sk-SK")}</strong></div>
                <div className="settings-line"><b>API-set graph edges</b><strong>{runtimeInfo.staticAudit.boundedGraphApiSetEdges.toLocaleString("sk-SK")}</strong></div>
                <div className="settings-line"><b>Deep edges without filename candidate</b><Tag kind="pending">{runtimeInfo.staticAudit.boundedGraphNoFilenameCandidateEdges} · NOT LOADER FAILURES</Tag></div>
                <div className="soft-warning">Všetkých 36 priamych názvov bolo klasifikovaných; úplná rekurzia, API-set presmerovania a dynamické LoadLibrary stále nie sú overené. Systémové DLL nie sú súčasťou navrhovaného inštalačného balíka.</div>
              </Panel>
              <Panel eyebrow="NW025-Z · ACTUAL WINDOWS LOAD PROBE" title="Scoped runtime observation" extra={<Tag kind="tested">20/20 PASS</Tag>}>
                <div className="native-release-metrics">
                  <div><strong>{runtimeInfo.loadedModuleAudit.runtimeModules}</strong><span>Historical isolated Python runtime modules</span></div>
                  <div><strong>{runtimeInfo.loadedModuleAudit.windowsLocationModules}</strong><span>Windows system module locations</span></div>
                  <div><strong>{runtimeInfo.loadedModuleAudit.unexpectedModuleLocations}</strong><span>Unexpected module locations</span></div>
                </div>
                <div className="settings-line"><b>Test source</b><strong>Isolated NW025-Y runtime</strong></div>
                <div className="settings-line"><b>Runtime hashes matched manifest</b><Tag kind="tested">YES · LOCAL SHA</Tag></div>
                <div className="settings-line"><b>Transient loader history</b><Tag kind="hold">NOT CAPTURED</Tag></div>
                <div className="settings-line"><b>Clean-machine relocation</b><Tag kind="hold">NOT TESTED</Tag></div>
                <div className="settings-line"><b>Host requests launched by evidence test</b><strong>0</strong></div>
                <div className="soft-warning">Pozorovaných 40 modulov je snímka po obmedzených testoch, nie kompletný zoznam všetkých možných runtime závislostí. Nejde o produkčný test Studio Hostu ani inštalátora.</div>
              </Panel>
            </div>
            <div className="two-col">
              <Panel eyebrow="RUNTIME DEPLOYMENT INVENTORY" title="Seventeen source-indexed runtime modules" extra={<Tag kind="blue">READ-ONLY PINS</Tag>}>
                <input className="native-gate-filter" aria-label="Find observed runtime module" value={nativeModuleQuery}
                  onChange={e=>setNativeModuleQuery(e.target.value)} placeholder="Filter runtime module filename…" />
                <div className="runtime-module-list">
                  {filteredNativeModules.map(entry=><div className="runtime-module" key={entry.fileName}>
                    <div><b>{entry.fileName}</b><small>{entry.bytes.toLocaleString("sk-SK")} bytes · observed in NW025-Z, not a shipping manifest</small></div>
                    <code title={entry.sha256}>{shortHash(entry.sha256)}</code>
                  </div>)}
                  {filteredNativeModules.length===0 && <p className="empty">No observed runtime module matches the filter.</p>}
                </div>
              </Panel>
              <Panel eyebrow="LEGAL & RELEASE CONTROLS" title="Runtime notice and licensing">
                <div className="settings-line"><b>Python runtime notice</b><Tag kind="tested">CAPTURED · SHA PINNED</Tag></div>
                <div className="detail-section"><label>PYTHON NOTICE SOURCE SHA-256</label><code>{runtimeInfo.staticAudit.pythonLicenseSha256}</code></div>
                <div className="settings-line"><b>Node runtime version</b><strong>{runtimeInfo.staticAudit.nodeVersion}</strong></div>
                <div className="settings-line"><b>NW025-U historic Node notice</b><Tag kind="pending">NOT OBTAINED THEN</Tag></div>
                <div className="settings-line"><b>UI-008 exact Node LICENSE</b><Tag kind={nodeNoticeData?"tested":"hold"}>{nodeNoticeData?"SOURCE CAPTURED":"NOT VERIFIED"}</Tag></div>
                <div className="settings-line"><b>Version and installed binary</b><Tag kind={nodeNoticeData?"tested":"hold"}>{nodeNoticeData?"SHA MATCH":"UNKNOWN"}</Tag></div>
                <div className="settings-line"><b>Local node.exe Authenticode</b><Tag kind={nodeWindowsSignature?"tested":"hold"}>{nodeWindowsSignature?"VALID · OpenJS Foundation":"NOT VERIFIED"}</Tag></div>
                <div className="settings-line"><b>Third-party notices and legal review</b><Tag kind="hold">PENDING</Tag></div>
                <div className="settings-line"><b>Redistribution acceptance</b><Tag kind="hold">NOT APPROVED</Tag></div>
                <div className="settings-line"><b>Complete dependency closure</b><Tag kind="hold">UNVERIFIED</Tag></div>
                <div className="settings-line"><b>Signed setup</b><Tag kind="hold">NOT BUILT</Tag></div>
                <div className="soft-warning">Uložená Python licencia nie je dôkazom úplného pokrytia tretích strán. Node/npm/Corepack oznámenia nemožno zamieňať za schválený presný runtime notice bundle.</div>
              </Panel>
            </div>
            {nodeNoticeData && <Panel eyebrow="UI-008 / NEW OFFICIAL SOURCE EVIDENCE" title="Node 24.19.0 · License provenance" extra={<Tag kind="blue">LEGAL REVIEW REQUIRED</Tag>}>
              <div className="native-release-metrics">
                <div><strong>24.19.0</strong><span>Exact official Node release & local binary match</span></div>
                <div><strong>{nodeNoticeData.node.licenseBytes.toLocaleString("sk-SK")}</strong><span>LICENSE bytes extracted without installing Node</span></div>
                <div><strong>0</strong><span>Production signatures or redistribution approvals granted</span></div>
              </div>
              <div className="two-col">
                <div className="node-notice-evidence">
                  <div className="detail-section"><label>OFFICIAL DISTRIBUTION SHA-256 · TLS SOURCE, NOT SIGNED IDENTITY</label><code>{nodeNoticeData.node.sourceNodeArchiveSha256}</code></div>
                  <div className="detail-section"><label>LICENSE SHA-256 · VERSION-MATCHED</label><code>{nodeNoticeData.node.licenseSha256}</code></div>
                  <div className="detail-section"><label>LOCAL INSTALLED NODE.EXE SHA-256 · MATCHED ARCHIVE BYTE-EXACT</label><code>{nodeNoticeData.node.installedNodeExeSha256}</code></div>
                </div>
                <div className="node-notice-evidence">
                  <div className="settings-line"><b>Official version-matched LICENSE</b><Tag kind="tested">OBTAINED</Tag></div>
                  <div className="settings-line"><b>Archive & local node.exe</b><Tag kind="tested">SHA MATCH</Tag></div>
                  <div className="settings-line"><b>Node.exe Windows Authenticode</b><Tag kind={nodeWindowsSignature?"tested":"hold"}>{nodeWindowsSignature?"VALID · OPENJS":"NOT VERIFIED"}</Tag></div>
                  <div className="settings-line"><b>SHASUMS detached release signature</b><Tag kind="hold">NOT VERIFIED</Tag></div>
                  <div className="settings-line"><b>npm/Corepack & other notices</b><Tag kind="hold">LEGAL AUDIT OPEN</Tag></div>
                  <div className="settings-line"><b>Redistribution clearance</b><Tag kind="hold">NOT APPROVED</Tag></div>
                </div>
              </div>
              <div className="node-license-link"><a href="./notices/node-v24.19.0-LICENSE.txt" target="_blank" rel="noopener noreferrer">Open exact Node 24.19.0 LICENSE (bundled text) ↗</a><span>Local static file · SHA-256 validated · no download or execution of Node binaries</span></div>
              <div className="soft-warning">NW025-U historically reported the Node runtime notice as missing; that original evidence remains unchanged. UI-008 adds newer version-matched licensing evidence only. This does NOT permit shipping node.exe, installing a component, enabling workers, or claiming publisher/Owner/Witness authenticity.</div>
            </Panel>}
            <Panel eyebrow="NO-GO RELEASE EVIDENCE" title="Seven historical packaging blockers" extra={<Tag kind="hold">REVIEW REMAINS OPEN</Tag>}>
              <div className="native-release-blockers">
                {PACKAGING_BLOCKERS.map((reason,i)=><div className="native-release-blocker" key={reason}>
                  <span>{String(i+1).padStart(2,"0")}</span><div><strong>{reason}</strong><small>{BLOCKER_DESCRIPTIONS[reason]}</small>{reason==="NODE_RUNTIME_LICENSE_NOTICE_NOT_OBTAINED" && nodeNoticeData && <small>UI-008 update: the exact Node LICENSE is now captured; separate legal review and complete npm/Corepack notice coverage remain open.</small>}</div><Tag kind={reason==="NODE_RUNTIME_LICENSE_NOTICE_NOT_OBTAINED" && nodeNoticeData?"pending":"hold"}>{reason==="NODE_RUNTIME_LICENSE_NOTICE_NOT_OBTAINED" && nodeNoticeData?"REVIEW PENDING":"OPEN"}</Tag>
                </div>)}
              </div>
            </Panel>
            <Panel eyebrow="CRYPTOGRAPHIC SOURCE LINEAGE" title="Immutable source evidence">
              <div className="crossplane-hashes">{Object.entries(runtimeInfo.sourcePins).map(([name,hash])=>
                <div key={name}><strong>{name}</strong><code>{hash}</code></div>)}</div>
              <p className="native-module-note">Original NW025 evidence is pinned with local SHA-256. Two independently scoped research candidates are correlated for presentation only. No system DLL, original game corpus or original runtime binary is shipped in this UI candidate.</p>
              <div className="mini-list">{["native_dependencies","native_loads"].map(smallModule)}</div>
            </Panel>
          </> : <div className="soft-warning">Pinned NW025-U/Z evidence rejected or unavailable. No release or loader correctness can be inferred; production remains HOLD.</div>}
        </>}
        {page === "security" && <>
          <div className="page-intro">
            <div className="eyebrow">PLATFORM / WINDOWS IDENTITY RESEARCH</div>
            <h1>Host Security Lab<span className="title-dot">.</span></h1>
            <p>Overená identita jedného lokálneho Windows klienta. Výsledok pochádza z testov OS impersonácie cez named pipe, nie z podpísaného Owner/Witness kanála. Bez externého trustu zostávajú production gate, inštalátor aj dispatch zamknuté.</p>
          </div>
          <div className="section-banner"><Tag kind="hold">PRODUCTION HOLD</Tag>
            <span>Actual same-user SID comparison passed · distinct role SID and signed installation are NOT verified.</span>
          </div>
          {securityData ? <>
            <div className="metric-grid">
              <Metric label="Real Windows token tests" value={securityData.osProof.testCount + "/16"} desc="Same-user impersonation and negative tests" />
              <Metric label="OS client SID match" value="PASS" desc="Compared internally, value not saved" />
              <Metric label="Different-role SID verified" value="0" desc="Cross-account authorization still missing" attention />
              <Metric label="Accepted release components" value="0 / 9" desc="Plan evidence, not a live OS inventory" attention />
            </div>
            <div className="hero-card hero-short security-hero">
              <div><div className="hero-eyebrow">REAL WINDOWS LOCAL PROOF</div>
                <h2>Impersonation tested.<br/><span>Production identity not admitted.</span></h2>
                <p>NamedPipeServerStream · CurrentUserOnly · RunAsClient · WindowsIdentity.GetCurrent(true). Client SID compared within an actual impersonation context, without persisting the user's SID or token material.</p>
              </div>
              <div className="hero-status"><span>HOST AUTHORIZATION</span><b>HOLD</b><small>NOT EXTERNALLY SIGNED</small></div>
            </div>
            <div className="two-col">
              <Panel eyebrow="WINDOWS NATIVE TEST RESULT" title="IPC identity evidence" extra={<Tag kind="tested">16/16 LOCAL PASS</Tag>}>
                <div className="security-flow">
                  <div><span>01</span><strong>OS named pipe</strong><small>CurrentUserOnly · one request</small></div>
                  <div><span>02</span><strong>Client impersonation</strong><small>Real Windows token comparison</small></div>
                  <div><span>03</span><strong>Local read-only reply</strong><small>HOLD · no Owner authority</small></div>
                </div>
                <div className="settings-line"><b>Same-user impersonation</b><Tag kind="tested">OS VERIFIED</Tag></div>
                <div className="settings-line"><b>SID stored in logs</b><strong>NO</strong></div>
                <div className="settings-line"><b>Weaker impersonation level</b><Tag kind="tested">FAIL-CLOSED</Tag></div>
                <div className="settings-line"><b>Different Windows account tested</b><Tag kind="hold">NOT TESTED</Tag></div>
                <div className="settings-line"><b>Owner / Witness signature chain</b><Tag kind="hold">MISSING</Tag></div>
                <div className="soft-warning">A matching client SID proves a local account match, not a separated native worker token, protected install identity or independent production Owner/Witness admission.</div>
                <button className="secondary-button" onClick={() => setPage("native")}>Review Native IPC Lab →</button>
              </Panel>
              <Panel eyebrow="ONE INSTALLER / COMPLETE PLATFORM" title="Release and deployment" extra={<Tag kind="pending">DESIGN ONLY</Tag>}>
                <div className="settings-line"><b>Planned setup</b><strong className="security-filename">{securityData.installReadiness.oneInstallerIdentity}</strong></div>
                <div className="settings-line"><b>Mandatory components</b><strong>{securityData.installReadiness.requiredComponentCount}</strong></div>
                <div className="settings-line"><b>Accepted production components</b><Tag kind="hold">ZERO VERIFIED</Tag></div>
                <div className="settings-line"><b>Windows Rust/Cargo toolchain</b><Tag kind="hold">NOT FOUND</Tag></div>
                <div className="settings-line"><b>Tauri 2 compiled GUI</b><Tag kind="hold">NOT BUILT</Tag></div>
                <div className="settings-line"><b>Full Python/Node DLL closure</b><Tag kind="hold">NOT VERIFIED</Tag></div>
                <div className="settings-line"><b>Approved original Studio icon</b><Tag kind="pending">NOT LOCATED</Tag></div>
                <div className="soft-warning">The single Windows installer and full local runtime stack are approved requirements, not delivered binaries. This diagnostic UI cannot install, sign or start components.</div>
                <button className="secondary-button" onClick={() => setPage("components")}>Open Component Manager plan →</button>
              </Panel>
            </div>
            <Panel eyebrow="TRUST / RELEASE ENTRY GATES" title="Production prerequisites" extra={<Tag kind="hold">NONE ACCEPTED</Tag>}>
              <div className="security-filter" aria-label="Filter security gates">
                {(["all","identity","authority","release"] as const).map(k=>
                  <button key={k} className={securityArea===k?"active":""} onClick={()=>setSecurityArea(k)} aria-pressed={securityArea===k}>
                    {k==="all"?"All requirements":k==="identity"?"Windows identity":k==="authority"?"Owner / Witness":"Installer & runtime"}
                  </button>)}
              </div>
              <div className="security-gate-grid">
                {displayedSecurityGates.map(g=><div className="security-gate" key={g.id}>
                  <span className="gate-number">{String(RELEASE_SECURITY_GATES.indexOf(g)+1).padStart(2,"0")}</span>
                  <div><strong>{g.label}</strong><small>{g.role.toUpperCase()} · external acceptance required</small></div><Tag kind="hold">HOLD</Tag>
                </div>)}
              </div>
            </Panel>
            <Panel eyebrow="PINNED DIAGNOSTIC SOURCE" title="Evidence identity" extra={<Tag kind="blue">SHA-256 ONLY</Tag>}>
              <div className="security-pins">{Object.entries(securityData.sourcePins).map(([role,digest])=>
                <div key={role}><strong>{role}</strong><code>{digest}</code></div>)}</div>
              <div className="crossplane-owner-meta">Recorded {dateDisplay(securityData.generatedUtc)} · {securityData.sourceAuthority} · No source files were repinned from browser input</div>
              <p className="security-qualifier">{securityData.qualifier}</p>
            </Panel>
          </> : <div className="soft-warning">Pinned Windows security evidence is absent or rejected ({securityView.code}). No identity, signature, installer or production readiness may be inferred.</div>}
        </>}
        {page === "architecture" && <>
          <div className="page-intro">
            <div className="eyebrow">FRAMEWORK / CAPABILITIES · COMPLETION · FIDELITY</div>
            <h1>Architecture & Completion<span className="title-dot">.</span></h1>
            <p>Zdrojovo overených deväť schopností Frameworku. Väzby na Completion Intelligence a First-Divergence sú pripravené ako samostatné nástroje; na skutočné meranie autentického herného runtime stále potrebujú pôvodnú hru, porovnateľný replay a nezávislý oracle.</p>
          </div>
          <div className="section-banner"><Tag kind="hold">ARCHIVED / PRODUCTION HOLD</Tag>
            <span>16 pinned original source roles · no current owner, worker or authentic game comparison</span>
            <button className="top-button" onClick={()=>setPage("trust")}>Owner A/B/C review ↗</button>
          </div>
          {architecture ? <>
            <div className="metric-grid">
              <Metric label="Capability nodes" value={architecture.capabilities.length} desc="Independently source-indexed contracts"/>
              <Metric label="Source roles" value={architecture.sourceCount} desc="SHA-256 identity, not signature"/>
              <Metric label="Live game fidelity" value="0" desc="No original runtime replay was executed"/>
              <Metric label="Production authority" value="HOLD" desc="No current Owner/Witness or GUI lease" attention/>
            </div>
            <div className="hero-card hero-short architecture-hero">
              <div><div className="hero-eyebrow">CAPABILITY & DEPENDENCY GRAPH</div>
                <h2>One framework.<br/><span>Evidence before execution.</span></h2>
                <p>K003 remains the only authority-bearing scheduler. Completion prioritization is advisory, First-Divergence is diagnostic and every cross-game mechanic must pass its own fidelity validation.</p>
              </div>
              <div className="hero-status"><span>EXECUTION GATE</span><b>HOLD</b><small>NO NEW SCHEDULER</small></div>
            </div>
            <div className="two-col">
              <Panel eyebrow="NINE HISTORICAL CAPABILITIES" title="Dependency-linked modules" extra={<Tag kind="blue">READ-ONLY GRAPH</Tag>}>
                <div className="architecture-capabilities">
                  {architecture.capabilities.map((cap,i)=><button key={cap.id}
                    className={"architecture-cap "+(selectedCapabilityInfo?.id===cap.id?"selected":"")}
                    onClick={()=>setSelectedCapability(cap.id)}>
                    <span className="architecture-cap-index">{String(i+1).padStart(2,"0")}</span>
                    <span className="architecture-cap-content">
                      <strong>{cap.id}</strong>
                      <small>{cap.kind.toUpperCase()} · {cap.requires.length} prerequisites</small>
                    </span>
                    <Tag kind={cap.status.includes("BLOCKED")?"hold":"pending"}>{cap.status.includes("BLOCKED")?"BLOCKED":"SOURCE ONLY"}</Tag>
                  </button>)}
                </div>
              </Panel>
              <Panel eyebrow="SELECTED CONTRACT / NOT A WORKER" title={selectedCapabilityInfo?.id??"Capability missing"} extra={<Tag kind="hold">NOT DEPLOYED</Tag>}>
                {selectedCapabilityInfo && <>
                  <div className="settings-line"><b>Capability type</b><strong>{selectedCapabilityInfo.kind.toUpperCase()}</strong></div>
                  <div className="detail-section"><label>ORIGINAL STATUS</label><code>{selectedCapabilityInfo.status}</code></div>
                  <div className="detail-section"><label>REQUIRES</label>
                    {selectedCapabilityInfo.requires.length===0?<p>Root admission — external Owner/Witness acceptance required</p>:
                    <div className="architecture-dependencies">{selectedCapabilityInfo.requires.map(id=>
                      <button className="architecture-dependency" key={id} onClick={()=>setSelectedCapability(id)}>
                        <span>{id}</span><Tag kind="hold">NOT RELEASED</Tag>
                      </button>)}</div>}
                  </div>
                  <div className="detail-section"><label>REQUIRED BY</label>
                    <div className="architecture-dependencies">{architecture.capabilities
                      .filter(c=>c.requires.includes(selectedCapabilityInfo.id))
                      .map(c=><button key={c.id} className="architecture-dependency" onClick={()=>setSelectedCapability(c.id)}>
                        <span>{c.id}</span><Tag kind="pending">DEPENDENT</Tag>
                      </button>)}
                    {!architecture.capabilities.some(c=>c.requires.includes(selectedCapabilityInfo.id))&&<p>No dependent nodes in this bounded catalog</p>}</div>
                  </div>
                  <div className="soft-warning">Source-bound availability does not certify a component's installed version, active worker, authenticated Owner, cross-game equivalence or native runtime readiness.</div>
                  <button className="secondary-button" onClick={()=>setPage("compat")}>Review signed component requirements →</button>
                </>}
              </Panel>
            </div>
            <div className="three-notes architecture-modes">
              <div><b>Completion Intelligence</b><p>Advisory planning exists in isolated source. Authentic gameplay completion requires aligned input and owner-controlled evidence.</p><Tag kind="pending">INPUT REQUIRED</Tag></div>
              <div><b>First-Divergence Debugger</b><p>Bounded trace comparison code is source verified. There is no new game-specific replay or native oracle in this Studio screen.</p><Tag kind="pending">REPLAY REQUIRED</Tag></div>
              <div><b>Cross-Game Runtime IR</b><p>Asset, World, State, animation and gameplay contracts are proposed; reuse is gated by each original game's independent validation.</p><Tag kind="hold">NO GLOBAL FIDELITY PASS</Tag></div>
            </div>
            <Panel eyebrow="PORTABLE RELEASE POLICY / SOURCE LINEAGE" title="What is not yet accepted" extra={<Tag kind="hold">NO-GO</Tag>}>
              <div className="three-notes">
                <div><b>Runtime proof</b><p>Protected Studio install, signed EXE and approved original icon remain unverified.</p></div>
                <div><b>Host contract</b><p>GET/HEAD fixed snapshot only. No new native method or process execution endpoint.</p></div>
                <div><b>External control</b><p>A → B → C are independently reviewed. Local SHA cannot elect a production Owner or Witness.</p></div>
              </div>
              <div className="row-actions"><button className="secondary-button" onClick={()=>setPage("completion")}>Inspect real game blockers →</button><button className="secondary-button" onClick={()=>setPage("nexttask")}>View bounded next-task fixtures →</button></div>
            </Panel>
          </> : <div className="soft-warning">Architecture contract/source failed strict validation. Capability details withheld; no execution authority inferred.</div>}
        </>}
        {page === "nexttask" && <NextTaskLab view={boundedView} busy={boundedBusy}
          onReload={reloadBoundedPlanEvidence} onCrossplane={()=>setPage("crossplane")}/>}
        {page === "crossplane" && <>
          <CoreOrionPanel/>{new URLSearchParams(window.location.search).get("canonicalTest")==="1" && <CanonicalCorePanel/>}
          <div className="page-intro"><div className="eyebrow">PLATFORM / FRAMEWORK ↔ ORION EVIDENCE</div><h1>Orchestration crossplane<span className="title-dot">.</span></h1>
            <p>Zdrojovo pripnutý historický audit K003, ORION a Owner/Witness. Záznamy s rôznymi časmi nie sú jednou živou transakciou. ORION nie je druhý scheduler.</p>
          </div>
          <div className="section-banner"><Tag kind="hold">{crossplaneView.phase==="HOLD"?"CAPTURE UNAVAILABLE":"ARCHIVED / PROD HOLD"}</Tag>
            <span>Model execution: BLOCKED · independent Owner/Witness: NOT ACCEPTED · {crossplaneView.code}</span>
            <button className="top-button" disabled={crossplaneBusy} onClick={reloadCrossplaneCapture}>{crossplaneBusy?"Reading…":"Reload saved snapshot"}</button>
          </div>
          <div className="metric-grid">
            <Metric label="Pinned source roles" value={crossplaneData ? Object.keys(crossplaneData.sourceHashes).length : 0} desc="Historical fixed scope"/>
            <Metric label="ORION shadow tasks" value={crossplaneData?.tasks.length??0} desc="No eligible model profile"/>
            <Metric label="Live workers verified" value="0" desc="Historical is not live"/>
            <Metric label="Production authorization" value="HOLD" desc="Signed Owner/Witness absent" attention/>
          </div>
          {crossplaneView.phase==="HOLD" && <div className="soft-warning">No valid source-bound record is available. Previous cards were cleared; no retry, fallback or job submission.</div>}
          {crossplaneData && <>
            <div className="soft-warning"><strong>Archived evidence only:</strong> Native Worker state was {crossplaneData.nativeHistoricalState} at the source observation. It was already {crossplaneData.nativeAgeSeconds?.toFixed(0)} seconds old when captured. No current Windows task/service status is asserted. Captured {crossplaneData.capturedUtc ? dateDisplay(crossplaneData.capturedUtc) : "unknown"}.</div>
            <div className="two-col">
              <Panel eyebrow="R11 / SHADOW TASKS" title="Five ORION proposals" extra={<Tag kind="hold">NO DISPATCH</Tag>}>
                <div className="checkpoint-list">{crossplaneData.tasks.map(task=><div className="crossplane-task" key={task.taskId}>
                  <div className="checkpoint-row"><strong>{task.taskId} · {task.orionStatus}</strong><Tag kind="hold">HOLD</Tag></div>
                  <div className="crossplane-task-title">{task.routeReason}</div><div className="source-path">{task.operationId}</div>
                  <div className="source-path">SHA: {shortHash(task.inputSha256)}</div><small>No model, native worker or dispatch executed</small>
                </div>)}</div>
              </Panel>
              <Panel eyebrow="EXECUTION GATES" title="Why dispatch remains blocked" extra={<Tag kind="hold">FAIL-CLOSED</Tag>}>
                <div className="crossplane-reason-list">{crossplaneData.reasonCodes.map(reason=>
                  <div className="crossplane-reason" key={reason}><span>!</span><strong>{reason}</strong></div>)}</div>
              </Panel>
            </div>
            <Panel eyebrow="PROVENANCE" title="Twelve pinned source inputs" extra={<Tag kind="blue">UNSIGNED SHA ONLY</Tag>}>
              <div className="three-notes">
                <div><b>Manifest SHA</b><p className="break-any">{crossplaneData.manifestSha256}</p></div>
                <div><b>Work-package SHA</b><p className="break-any">{crossplaneData.workPackageSha256}</p></div>
                <div><b>Diagnostic</b><p>CLI exit {crossplaneData.cliExitCode} means HOLD, never production acceptance.</p></div>
              </div>
              <details className="crossplane-details"><summary>Show all twelve SHA-256 source roles</summary><div className="crossplane-hashes">
                {Object.entries(crossplaneData.sourceHashes).map(([role,digest])=><div key={role}><strong>{role}</strong><code>{digest}</code></div>)}
              </div></details>
            </Panel>
          </>}
          <Panel eyebrow="SEPARATE OWNER / WITNESS R8 SNAPSHOT" title="Owner admission review" extra={<Tag kind="hold">NOT INDEPENDENTLY SIGNED</Tag>}>
            {ownerReview.sourceEvidence ? <>
              <div className="crossplane-owner-meta">Historical same-assistant review · source timestamp {dateDisplay(ownerReview.sourceEvidence.created_host_clock_not_external_signer)} · not live service attestation</div>
              <div className="metric-grid compact-metrics">
                <Metric label="R8 reported regressions" value={ownerReview.sourceEvidence.new_regression_tests_passed} desc="Isolated software tests"/>
                <Metric label="Shadow K003 cases" value={ownerReview.sourceEvidence.real_synthetic_windows_K003_process_scenarios} desc="Synthetic Windows processes"/>
                <Metric label="Source roles SHA verified" value={ownerReview.sourceEvidence.source_roles_sha_verified} desc="Not independent signature"/>
                <Metric label="Owner/Witness accepted" value="0" desc="Authority withheld" attention/>
              </div>
              <div className="crossplane-owner-gates">{OWNER_GATES.map(g=><div key={g.id}><span>{g.label}</span><Tag kind="hold">UNVERIFIED</Tag></div>)}</div>
              <div className="soft-warning">Reported Native Task: {ownerReview.sourceEvidence.native_task} · Gateway: {ownerReview.sourceEvidence.gateway_task}. Historical text only, not current live status. No lease, installer or worker dispatch permitted.</div>
            </> : <div className="soft-warning">Owner/Witness source checkpoint rejected or unavailable. No authority may be inferred.</div>}
            <div className="mini-list">{["orion_studio_bridge","owner_witness_review"].map(smallModule)}</div>
          </Panel>
          <div className="three-notes crossplane-footer">
            <div><b>One scheduler</b><p>Only K003 owns production orchestration; ORION is a candidate routing layer.</p></div>
            <div><b>Read-only browser</b><p>Reload reads fixed stored evidence; no Host/worker/model execution.</p></div>
            <div><b>Next acceptance</b><p>Independent Owner custody, off-host Witness and signed role receipts must be separately reviewed.</p></div>
          </div>
        </>}
        {page === "native" && <>
          <div className="page-intro">
            <div className="eyebrow">PLATFORM / WINDOWS IPC RESEARCH</div>
            <h1>Native IPC Lab<span className="title-dot">.</span></h1>
            <p>Skutočne otestovaný jednorazový Windows named-pipe prototyp a read-only audit PE závislostí. Nie je to produkčný Host, Tauri IPC integrácia ani schválený Windows inštalátor.</p>
          </div>
          <div className="section-banner native-banner">
            <Tag kind="hold">PRODUCTION HOLD</Tag><span>Role tokens, signed Owner/Witness, protected install root and kompletné runtime závislosti neboli prijaté.</span>
            <button className="top-button" disabled={!ipc.report} onClick={exportNativeReport}>Export audit ↓</button>
          </div>
          {ipc.report ? <>
            <div className="metric-grid">
              <Metric label="Windows IPC tests" value={ipc.report.ipcPrototype.testCount + "/20"} desc="One-shot current-user-only prototype"/>
              <Metric label="Python direct DLLs" value={ipc.report.binaryClosure.binaries.python.directImportCount} desc="Name-only PE import scan"/>
              <Metric label="Node direct DLLs" value={ipc.report.binaryClosure.binaries.node.directImportCount} desc="Not a transitive dependency closure"/>
              <Metric label="Admission gates" value="0 / 12" desc="Independent production proof absent" attention/>
            </div>
            <div className="hero-card hero-short ipc-hero">
              <div><div className="hero-eyebrow">SOURCE-BOUND NATIVE PROTOTYPE</div>
                <h2>Windows IPC verified.<br/><span>Owner authorization unresolved.</span></h2>
                <p>.NET 9 NamedPipeServerStream with CurrentUserOnly, fixed read-only capture, strict request schema and zero job dispatch. Windows accounts with distinct role tokens were not tested.</p>
              </div><div className="hero-status"><span>PRODUCTION GATE</span><b>HOLD</b><small>NO EXTERNAL SIGNATURE</small></div>
            </div>
            <div className="two-col">
              <Panel eyebrow="REAL WINDOWS OBSERVATION" title="IPC boundary" extra={<Tag kind="tested">20 SELF-TESTS PASS</Tag>}>
                <div className="ipc-flow">
                  <div><span>01</span><strong>Studio UI</strong><small>Presentation only</small></div>
                  <div><span>02</span><strong>Native pipe POC</strong><small>Windows · one shot · same user</small></div>
                  <div><span>03</span><strong>Pinned archive</strong><small>Read-only / no Host invocation</small></div>
                </div>
                <div className="settings-line"><b>Transport</b><strong>Named pipe / CurrentUserOnly</strong></div>
                <div className="settings-line"><b>Request scope</b><strong>Health, List, Get</strong></div>
                <div className="settings-line"><b>Back-end lifecycle</b><strong>One request then exit</strong></div>
                <div className="settings-line"><b>Other-user SID validation</b><Tag kind="pending">NOT TESTED</Tag></div>
                <div className="settings-line"><b>Production Tauri Host integration</b><Tag kind="hold">NOT CONNECTED</Tag></div>
                <button className="secondary-button" onClick={()=>setPage("inspector")}>Inspect captured checkpoint evidence →</button>
              </Panel>
              <Panel eyebrow="PORTABILITY AUDIT" title="Executable import surface" extra={<Tag kind="pending">INCOMPLETE CLOSURE</Tag>}>
                <div className="native-tabs" role="tablist" aria-label="Runtime selector">
                  {(["python","node"] as const).map(name=><button key={name} role="tab" aria-selected={runtimeTab===name} className={runtimeTab===name?"active":""} onClick={()=>setRuntimeTab(name)}>{name==="python"?"Python 3.14":"Node.js 24"}</button>)}
                </div>
                {auditedRuntime && <>
                  <div className="native-image-summary"><div><span>IMAGE</span><strong>{auditedRuntime.fileName}</strong></div><div><span>DIRECT IMPORTS</span><strong>{auditedRuntime.directImportCount}</strong></div><div><span>MACHINE</span><strong>{auditedRuntime.machineHex}</strong></div></div>
                  <div className="detail-section"><label>LOCAL IMAGE SHA-256 (NOT PUBLISHER SIGNATURE)</label><code>{auditedRuntime.sha256}</code></div>
                  <div className="detail-section"><label>OBSERVED IMPORT NAMES</label><div className="dll-list">{auditedRuntime.directImportDllNames.map(name=><span key={name}>{name}</span>)}</div></div>
                </>}
                <div className="soft-warning">Direct DLL names were extracted from actual pinned PE files. Delay imports, transitive DLL trees, package licenses and loader behavior remain unverified.</div>
              </Panel>
            </div>
            <Panel eyebrow="RELEASE ADMISSION CROSSWALK" title="Required production gates" extra={<Tag kind="hold">ALL PENDING</Tag>}>
              <div className="native-gate-intro">Tento prehľad nemožno prepnutím v UI povýšiť na PASS. Každý bod vyžaduje samostatný nezávisle akceptovaný dôkaz.</div>
              <input className="native-gate-filter" aria-label="Filter native admission requirements" value={gateSearch} onChange={e=>setGateSearch(e.target.value)} placeholder="Filter prerequisites…" />
              <div className="native-gate-grid">
                {missingAdmissionGates.map(key=><div className="native-gate" key={key}><span className="gate-number">{String(REQUIRED_ADMISSION_GATES.indexOf(key)+1).padStart(2,"0")}</span><span className="native-gate-name">{ADMISSION_LABELS[key]}</span><Tag kind="hold">MISSING</Tag></div>)}
                {missingAdmissionGates.length===0 && <p className="empty">No matching admission gate.</p>}
              </div>
            </Panel>
            <div className="two-col">
              <Panel eyebrow="REUSED TESTED MODULES" title="Pinned platform dependencies">
                <div className="mini-list">{["host_api","inspector_controller","diagnostics_host"].map(smallModule)}</div>
                <p className="native-module-note">Inspector Controller r1 already implements one in-flight request, one queued request and stale-view clearing. Diagnostics Host r2 currently covers synthetic fixtures only.</p>
              </Panel>
              <Panel eyebrow="FINAL RELEASE IDENTITY" title="One Installer · Modular Runtime">
                <div className="settings-line"><b>Setup filename</b><strong>OpenRemasterStudio-Setup-x64.exe</strong></div>
                <div className="settings-line"><b>Existing Studio icon</b><Tag kind="pending">ASSET NOT VERIFIED</Tag></div>
                <div className="settings-line"><b>Signed native EXE</b><Tag kind="hold">NOT BUILT</Tag></div>
                <div className="settings-line"><b>Component Manager</b><Tag kind="pending">DESIGN ONLY</Tag></div>
                <div className="soft-warning">Tento kandidát nevytvára náhradnú značku ani nepreberá autoritu existujúceho K003. Pozorovanie IPC nevytvára povolenie na spustenie Native Worker V2.</div>
                <button className="secondary-button" onClick={()=>setPage("components")}>View component plan →</button>
              </Panel>
            </div>
          </> : <div className="soft-warning">Native readiness report was rejected or missing ({ipc.reason}). No tested or admitted status can be inferred.</div>}
        </>}
        {page === "completion" && <GameCompletionLab data={gameCompletionState.data}
          onReload={reloadGameCompletion} busy={gameCompletionBusy}
          onArchitecture={()=>setPage("architecture")} onFidelity={()=>setPage("fidelity")}/>}
        {page === "projects" && <>
          <div className="page-intro"><div className="eyebrow">WORKSPACE / PROJECTS</div><h1>Project Workbench<span className="title-dot">.</span></h1><p>Register known game projects without opening their original media. Project status is deliberately not inferred from folder presence.</p></div>
          <div className="section-banner"><Tag kind="pending">NOT LIVE-BOUND</Tag><span>Per-project checkpoint API and authenticated owner leases are not connected.</span><button className="top-button" onClick={()=>setPage("completion")}>Source-bound game blockers ↗</button></div>
          <div className="project-grid">{snapshot.projects.map((p,i) => <div key={p.id} className="project-card"><div className="project-letter">{String(i+1).padStart(2,"0")}</div><h3>{p.id}</h3><small>Source corpus remains immutable</small><div className="project-foot"><Tag>RUNTIME NOT QUERIED</Tag><span>→</span></div></div>)}</div>
        </>}
        {page === "assets" && <>
          <div className="page-intro"><div className="eyebrow">CREATION / ASSET PIPELINE</div><h1>Asset Labs<span className="title-dot">.</span></h1><p>Asset restoration and capture tools will run as isolated on-demand components. A production shipping owner is not yet accepted.</p></div>
          <div className="two-col"><Panel eyebrow="PIPELINE" title="Asset Labs runtime contract"><div className="pipeline">{["Immutable source corpus","Source-indexed extracts & provenance","Derived preview data","Independent fidelity admission"].map((t,i) => <div key={t} className="pipeline-step"><span>{String(i+1).padStart(2,"0")}</span><div><b>{t}</b><small>{i === 3 ? "Required before a fidelity claim" : "Source-safe sidecar boundary"}</small></div></div>)}</div></Panel><Panel eyebrow="MODULE CONNECTION" title="Current readiness">{smallModule("asset_labs")}{smallModule("localization_lab")}<div className="soft-warning">Asset Labs is not a deployable production component yet. No originals are copied to an installer.</div></Panel></div>
        </>}
        {page === "fidelity" && <>
          <div className="page-intro"><div className="eyebrow">VALIDATION / FIDELITY</div><h1>Fidelity Gates<span className="title-dot">.</span></h1><p>Evidence before a fidelity score. Structural or technical tests alone cannot prove original-game equivalence.</p></div>
          <div className="two-col"><Panel eyebrow="VERSIONED CONTRACTS" title="Gate sequence"><div className="gate-list">{GATES.map(g => <div className="gate" key={g.id}><span>{g.id}</span><div><strong>{g.title}</strong><p>{g.detail}</p></div><Tag kind="blue">CONTRACT</Tag></div>)}</div></Panel><Panel eyebrow="SOURCE PROVENANCE" title="Fidelity & Evidence">{smallModule("fidelity_evidence")}{smallModule("evidence_adapters")}{smallModule("diagnostics_host")}<div className="soft-warning">No live game capture pair has been validated by this Studio UI. Fidelity PASS is unavailable.</div><button className="secondary-button" onClick={() => setPage("evidence")}>Inspect source hashes →</button></Panel></div>
        </>}
        {page === "intelligence" && <>
          <div className="page-intro"><div className="eyebrow">INTELLIGENCE / ORION</div><h1>Intelligence layer<span className="title-dot">.</span></h1><p>Deterministic-first routing, independent review and budget governance are separate from K003 execution authority.</p></div>
          <div className="hero-card hero-short"><div><div className="hero-eyebrow">SHADOW ORCHESTRATION</div><h2>Recommend, verify.<br/><span>Never self-authorize.</span></h2><p>No model calls, autonomous worker dispatch, or independent production signing from this console.</p></div><div className="hero-status"><span>ORION</span><b>HOLD</b><small>0 LIVE GATES ACCEPTED</small></div></div>
          <div className="two-col"><Panel eyebrow="MODEL CONTROL" title="ORION r3">{smallModule("orion")}<div className="three-notes compact"><div><b>Capability registry</b><p>Source-bound, versioned.</p></div><div><b>Independent review</b><p>External trust missing.</p></div><div><b>Budget governor</b><p>No cloud spend enabled.</p></div></div></Panel><Panel eyebrow="KNOWLEDGE" title="Read-only research layer">{smallModule("knowledge_bridge")}{smallModule("host_api")}<div className="soft-warning">KnowledgeBridge remains a separate research API. Inspector Host is the preferred shadow host; the APIs are not merged.</div></Panel></div>
        </>}
        {page === "governor" && <>
          <div className="page-intro"><div className="eyebrow">OPERATIONS / RESOURCE POLICY</div><h1>Governor<span className="title-dot">.</span></h1><p>GAME/LIGHT cooperative policy with worker acknowledgment and durable checkpoints; no forced process termination from UI.</p></div>
          <div className="metric-grid governor-metrics"><Metric label="Heavy workload ceiling" value={snapshot.policy.maxHeavySlots} desc="Global, not per component"/><Metric label="Writer policy" value="1" desc="Single authoritative writer"/><Metric label="Game autodetection" value="ON*" desc="Approved default, not runtime bound"/><Metric label="Resume behavior" value="HOLD" desc="Checkpoint required" attention/></div>
          <div className="two-col"><Panel eyebrow="GOVERNOR BRIDGE" title="Existing implementation">{smallModule("governor")}<div className="soft-warning">No live utilization/temperature telemetry or game-process state is queried by this console.</div></Panel><Panel eyebrow="RUNTIME LOGIC" title="Policy preview"><div className="mode-pill"><span>DETECTED GAME</span><b>GAME / LIGHT</b></div><div className="pipeline"><div className="pipeline-step"><span>01</span><div><b>Cooperative pause proposal</b><small>Not equivalent to a worker acknowledgment</small></div></div><div className="pipeline-step"><span>02</span><div><b>Durable checkpoint verification</b><small>Fail closed on missing receipt</small></div></div><div className="pipeline-step"><span>03</span><div><b>Safe resume after game exit</b><small>Requires owner/writer/resource gates</small></div></div></div></Panel></div>
        </>}
        {page === "localization" && <>
          <div className="page-intro"><div className="eyebrow">CREATION / LANGUAGE ASSETS</div><h1>Localization Lab<span className="title-dot">.</span></h1><p>Offline text catalogs, translation validation and font fallback, while original game resources remain untouched.</p></div><div className="two-col"><Panel eyebrow="MODULE CONNECTOR" title="Localization Lab 0.1.0">{smallModule("localization_lab")}<div className="detail-section"><label>GAME ADAPTER</label><strong>Generic JSON baseline</strong><small>Game-specific runtime overlay remains an admission task.</small></div></Panel><Panel eyebrow="ACCEPTANCE BOUNDARY" title="Translation pipeline"><div className="pipeline">{["Extract only from verified source","Map keys & provenance","Validate translation and font fallback","Admit real in-game overlay separately"].map((p,i)=><div className="pipeline-step" key={p}><span>{String(i+1).padStart(2,"0")}</span><div><b>{p}</b></div></div>)}</div></Panel></div>
        </>}
        {page === "evidence" && <>
          <div className="page-intro"><div className="eyebrow">AUDIT / EVIDENCE</div><h1>Evidence browser<span className="title-dot">.</span></h1><p>Every digest below is computed against an explicitly allowlisted local file. It proves local content consistency, not publisher identity or external attestation.</p></div>
          <div className="section-banner"><Tag kind={imported ? "pending" : "blue"}>{imported ? "IMPORTED / UNTRUSTED" : "LOCAL ALLOWLIST"}</Tag><span>Generated {dateDisplay(snapshot.generatedUtc)} · Live services NOT queried · No original game corpora opened</span><button className="text-action" onClick={exportSnapshot}>Export JSON ↓</button></div>
          <Panel eyebrow="CRYPTOGRAPHIC FILE INDEX" title="Checkpoint & source SHA-256"><div className="evidence-table"><div className="evidence-head"><span>MODULE</span><span>CHECKPOINT</span><span>SOURCE</span><span>ASSERTION</span></div>{modules.map(m=><div className="evidence-row" key={m.id}><strong>{m.title}</strong><span title={m.checkpointSha256 || ""}>{shortHash(m.checkpointSha256)}</span><span title={m.sourceSha256 || ""}>{shortHash(m.sourceSha256)}</span><ModuleBadge module={m}/></div>)}</div></Panel>
        </>}
        {page === "components" && <>
          <div className="page-intro"><div className="eyebrow">MANAGEMENT / DELIVERY</div><h1>Component Manager<span className="title-dot">.</span></h1><p>One Installer · Complete Platform · Modular Runtime. Source manifest is wired; installer/update actions remain disabled pending security admission.</p></div>
          <div className="section-banner"><Tag kind="hold">NO GO INSTALLER</Tag><span>Approved Windows app/setup icon must be reused; no substitute brand asset is generated.</span><button className="top-button" onClick={()=>setPage("trust")}>Review A/B/C gates</button></div>
          <Panel eyebrow="PLANNED WINDOWS X64 RELEASE" title="Mandatory platform components" extra={<Tag kind="blue">{snapshot.packaging.components.length} MANIFEST ENTRIES</Tag>}><div className="component-table"><div className="component-head"><span>COMPONENT</span><span>LAUNCH</span><span>ISOLATION</span><span>RELEASE</span></div>{snapshot.packaging.components.map(c=><div className="component-row" key={c.id}><strong>{lookup(c.id)?.title || c.id}</strong><span>{c.launchPolicy.replaceAll("_"," ").toUpperCase()}</span><span>{c.isolatedProcess ? "SEPARATE PROCESS" : "NOT PROVEN"}</span><Tag kind="hold">NO INSTALL RECEIPT</Tag></div>)}</div>
            <div className="component-footer"><div><strong>{snapshot.packaging.plannedSetup}</strong><small>Proposed identity, not an actual signed artifact</small></div><button className="disabled-button" disabled title="Independent publisher/owner/witness/install-root gates not accepted">Install / Update locked</button></div></Panel>
          <Panel eyebrow="NEW / SOURCE-BOUND PACKAGING EVIDENCE" title="Runtime dependency closure" extra={<Tag kind="hold">NO-GO</Tag>}>
            <div className="three-notes">
              <div><b>NW025-U · Static</b><p>36 classified direct names, but the 256-file graph hit its inspection limit.</p></div>
              <div><b>NW025-Z · Observed</b><p>20/20 scoped Windows tests and 40 modules recorded in a historical runtime snapshot.</p></div>
              <div><b>Node license source obtained</b><p>Exact Node v24.19.0 LICENSE is now SHA matched; redistribution review, full loader closure, signatures and native Tauri build remain open.</p></div>
            </div>
            <button className="secondary-button" onClick={()=>setPage("runtime")}>Inspect Native Runtime & Packaging →</button>
          </Panel>
          <Panel eyebrow="NEW / COMPATIBILITY CROSSWALK" title="Required protocols and release versions" extra={<Tag kind="hold">9/9 UNADMITTED</Tag>}>
            <div className="three-notes">
              <div><b>Nine planned components</b><p>Eight have source SHA evidence; one Asset Labs shipping entrypoint remains unresolved.</p></div>
              <div><b>Five required protocols</b><p>R6 / R10 / R11 / K003 / NativeWorkerV2 have no signed per-component bindings.</p></div>
              <div><b>Historical Witness r15</b><p>85 research tests; actual r15 receipt cryptography unverified and native provider blocked.</p></div>
            </div>
            <button className="secondary-button" onClick={()=>setPage("compat")}>Open Compatibility Lab →</button>
          </Panel>
          <Panel eyebrow="NEW / PORTABLE HOST INTEGRATION EVIDENCE" title="Source-bound Python + Node host" extra={<Tag kind="hold">PRODUCTION NOT ADMITTED</Tag>}>
            <div className="three-notes">
              <div><b>NW025-AC · Portable bindings</b><p>188 source-verified offline tests, 759 runtime files freshly rehashed, no PATH fallback.</p></div>
              <div><b>NW025-AD · Synthetic transport</b><p>Seven actual Windows Job-owned transport cases with a synthetic Python service.</p></div>
              <div><b>Production Host</b><p>Real Inspector, independent Owner/Witness, signed Tauri and clean-machine install remain unverified.</p></div>
            </div>
            <button className="secondary-button" onClick={()=>setPage("portable")}>Inspect Portable Host evidence →</button>
          </Panel>
        </>}
        {page === "compat" && <>
          <div className="page-intro">
            <div className="eyebrow">MANAGEMENT / VERSION & DEPLOYMENT VALIDATION</div>
            <h1>Compatibility Lab<span className="title-dot">.</span></h1>
            <p>Zdrojovo overená kontrola povinného Windows x64 balenia. Existujúci plán definuje komponenty a globálne protokoly, nie podpísané verzie jednotlivých binárok. Neznáme väzby automaticky znamenajú HOLD.</p>
          </div>
          <div className="section-banner"><Tag kind="hold">DEPLOYMENT NO-GO</Tag>
            <span>Version catalog missing · no production binaries admitted · {compView.kind}</span>
            <button className="top-button" onClick={()=>setPage("trust")}>External A/B/C gates ↗</button>
          </div>
          {comp ? <>
            <div className="metric-grid">
              <Metric label="Required components" value={comp.package.mandatoryComponentCount} desc="Frozen One Installer v1 plan"/>
              <Metric label="Observed source pins" value={comp.package.sourcePresentCount+" / 9"} desc="Local hashes, not signed releases"/>
              <Metric label="Signed binary versions" value="0 / 9" desc="No canonical signed version catalog" attention/>
              <Metric label="Protocol bindings" value="0 / 5" desc="Versioned R6/R10/R11/K003/V2 not admitted" attention/>
            </div>
            <div className="hero-card hero-short compat-hero"><div>
              <div className="hero-eyebrow">ONE INSTALLER · COMPLETE PLATFORM</div>
              <h2>Source inventory mapped.<br/><span>Compatibility not authenticated.</span></h2>
              <p>Všetkých deväť komponentových rolí sa zhoduje so zdrojovým plánom. Žiadna nie je schválená na nasadenie, zmenu vlastníka alebo spustenie. Source presence nie je binárna kompatibilita.</p>
            </div><div className="hero-status"><span>INSTALLER</span><b>NO-GO</b><small>ZERO SIGNED CATALOGS</small></div></div>
            <div className="two-col">
              <Panel eyebrow="SOURCE PLANNING CENSUS" title="Nine required component roles" extra={<Tag kind="pending">PLAN ONLY</Tag>}>
                <div className="security-filter">
                  {(["all","source","missing"] as const).map(s=><button key={s} className={compatFilter===s?"active":""}
                    aria-pressed={compatFilter===s} onClick={()=>setCompatFilter(s)}>
                    {s==="all"?"All nine":s==="source"?"Source observed (8)":"Unresolved (1)"}
                  </button>)}
                </div>
                <div className="compat-components">{listedComp.map(item=><button key={item.id}
                    className={"compat-component "+(activeComp?.id===item.id?"selected":"")}
                    onClick={()=>setSelectedCompat(item.id)}>
                    <span className="compat-mark">{item.historicalSourcePresent?"◇":"!"}</span>
                    <span className="compat-name"><strong>{item.title}</strong>
                      <small>{item.launchPolicy==="disabled_pending_external_trust"?"DISABLED / EXTERNAL TRUST":"PLANNED ON-DEMAND"}</small></span>
                    <Tag kind={item.historicalSourcePresent?"pending":"hold"}>{item.historicalSourcePresent?"SOURCE ONLY":"MISSING"}</Tag>
                  </button>)}</div>
              </Panel>
              <Panel eyebrow="SELECTED COMPONENT · NONEXECUTABLE" title={activeComp?.title ?? "No source selected"} extra={<Tag kind="hold">NOT ADMITTED</Tag>}>
                {activeComp && <>
                  <div className="settings-line"><b>Source file locally observed</b><Tag kind={activeComp.historicalSourcePresent?"blue":"hold"}>{activeComp.historicalSourcePresent?"YES · SHA ONLY":"NOT SELECTED"}</Tag></div>
                  <div className="settings-line"><b>Declared release label</b><strong>{activeComp.localReleaseLabel??"UNKNOWN"}</strong></div>
                  <div className="settings-line"><b>Canonical signed component version</b><Tag kind="hold">MISSING</Tag></div>
                  <div className="settings-line"><b>Protocol compatibility certificate</b><Tag kind="hold">NOT VERIFIED</Tag></div>
                  <div className="settings-line"><b>Protected installed binary receipt</b><Tag kind="hold">NOT FOUND</Tag></div>
                  <div className="settings-line"><b>Isolated process design</b><strong>REQUIRED</strong></div>
                  <div className="detail-section"><label>OBSERVED SOURCE HASH / NOT PUBLISHER SIGNATURE</label>
                    <code>{activeComp.sourceSha256??"NONE — canonical Asset Labs owner unresolved"}</code></div>
                  <div className="detail-section"><label>REQUIRED ACCEPTANCE EVIDENCE</label>
                    <div className="compat-missing">{PER_COMPONENT_MISSING.map((code,i)=><div key={code}>
                      <span>{String(i+1).padStart(2,"0")}</span><strong>{code.replaceAll("_"," ")}</strong><Tag kind="hold">UNKNOWN</Tag>
                    </div>)}</div>
                  </div>
                </>}
              </Panel>
            </div>
            <Panel eyebrow="COMPATIBILITY / GLOBAL REQUIRED PROTOCOLS" title="Five source-defined protocol requirements" extra={<Tag kind="hold">0 / 5 VERIFIED</Tag>}>
              <div className="compat-protocols">{REQUIRED_PROTOCOLS.map(p=><div key={p}>
                <b>{p}</b><span>PROTOCOL VERSION / BINARY BINDING NOT SIGNED</span><Tag kind="hold">HOLD</Tag></div>)}</div>
              <div className="three-notes compat-notes">
                <div><b>Windows architecture</b><p>{comp.package.minimumWindowsArchitecture} required by the source plan</p></div>
                <div><b>Unknown version</b><p>{comp.package.unknownVersionPolicy}: never assume a compatible unverified binary</p></div>
                <div><b>Downgrade rule</b><p>{comp.package.downgradePolicy}: never silently route to V1 or an older component</p></div>
              </div>
            </Panel>
            <Panel eyebrow="LOCAL ONLY / HYPOTHETICAL PREVIEW" title="Negative-first release preflight" extra={<Tag kind="hold">ALWAYS NO-GO</Tag>}>
              <div className="setting-row compat-sim-row"><div>
                <strong>Assume all source files were present</strong>
                <p>A view-only hypothetical. It does not add any source, binary, signature, version, component receipt or execution authority.</p>
              </div><button role="switch" aria-checked={whatIfSources} className={"toggle "+(whatIfSources?"on":"")}
                aria-label="Toggle hypothetical source presence only" onClick={()=>setWhatIfSources(x=>!x)}><span/></button></div>
              {dryComponent && <div className="compat-dry-grid">
                <div><strong>{dryComponent.sourceCount} / 9</strong><small>Source-presence assumption</small></div>
                <div><strong>{dryComponent.unsignedComponents}</strong><small>Unsigned component binaries</small></div>
                <div><strong>{dryComponent.unknownVersionContracts}</strong><small>Unknown component versions</small></div>
                <div><strong>NO-GO</strong><small>No installation, dispatch or version elevation</small></div>
              </div>}
              <div className="soft-warning">{dryComponent?.note} Neither this toggle nor an imported JSON file can grant authority. Unknown execution outcome always HOLD_NO_AUTO_RETRY.</div>
            </Panel>
            <div className="two-col">
              <Panel eyebrow="R15 HISTORICAL WITNESS RECEIPT REVIEW" title="Test-only signed receipt shape" extra={<Tag kind="hold">UNSIGNED SOURCE HOLD</Tag>}>
                <div className="native-release-metrics">
                  <div><strong>{comp.signedWitnessR15.historicalNegativeFirstTests}</strong><span>Historical negative-first unit tests</span></div>
                  <div><strong>{comp.signedWitnessR15.historicalSyntheticReceiptScenarios}</strong><span>Explicit synthetic receipt cases</span></div>
                  <div><strong>{comp.signedWitnessR15.sourceHashRoles}</strong><span>Locally SHA-pinned source roles</span></div>
                </div>
                <div className="settings-line"><b>Proposed signature format</b><strong>{comp.signedWitnessR15.proposedAlgorithm}</strong></div>
                <div className="settings-line"><b>Actual new receipt signature verified</b><Tag kind="hold">NO</Tag></div>
                <div className="settings-line"><b>Native CNG test invocation</b><Tag kind="hold">PROVIDER BLOCKED · NOT RETRIED</Tag></div>
                <div className="settings-line"><b>Current off-host Witness highwater</b><Tag kind="hold">NOT VERIFIED</Tag></div>
                <div className="settings-line"><b>Global fenced nonce CAS</b><Tag kind="hold">NOT VERIFIED</Tag></div>
                <div className="soft-warning">R15 validated a proposed wire shape using synthetic receipts and test-only bytes. This is not a valid signature for the new R15 receipt, trusted certificate, owner lease or permission to replay blocked native tests.</div>
              </Panel>
              <Panel eyebrow="FINAL RELEASE BOUNDARY" title="Compatibility ≠ authority" extra={<Tag kind="hold">PRODUCTION HOLD</Tag>}>
                <div className="settings-line"><b>Signed release catalog</b><Tag kind="hold">MISSING</Tag></div>
                <div className="settings-line"><b>Actual native Tauri executable</b><Tag kind="hold">NOT BUILT</Tag></div>
                <div className="settings-line"><b>Approved existing Studio icon</b><Tag kind="hold">NOT VERIFIED</Tag></div>
                <div className="settings-line"><b>Clean-machine install and rollback</b><Tag kind="hold">NOT TESTED</Tag></div>
                <div className="settings-line"><b>Distinct Windows role-token proof</b><Tag kind="hold">NOT ACCEPTED</Tag></div>
                <div className="settings-line"><b>External Owner A/B/C signoff</b><Tag kind="hold">MISSING</Tag></div>
                <div className="settings-line"><b>Live production Host RPC</b><Tag kind="hold">NOT CONNECTED</Tag></div>
                <div className="soft-warning">The source plan includes atomic staging and rollback design requirements. It provides no authenticated per-component dependency graph. Do not infer deployment ordering or component health from the plan's display order.</div>
                <button className="secondary-button" onClick={()=>setPage("trust")}>Inspect independent Owner A/B/C review →</button>
              </Panel>
            </div>
            <Panel eyebrow="SOURCE-PINNED READINESS" title="Original packaging and r15 receipt inputs" extra={<Tag kind="blue">LOCAL SHA · NOT SIGNATURE</Tag>}>
              <div className="crossplane-hashes">{Object.entries(comp.sourcePins).map(([role,digest])=><div key={role}>
                <strong>{role}</strong><code>{digest}</code></div>)}</div>
              <div className="mini-list">{["component_manager","signed_witness_boundary"].map(smallModule)}</div>
            </Panel>
          </> : <div className="soft-warning">Strict component compatibility evidence rejected or unavailable. No version, binary, install or runtime availability may be inferred.</div>}
        </>}
        {page === "trust" && <>
          <div className="page-intro">
            <div className="eyebrow">MANAGEMENT / RELEASE TRUST</div>
            <h1>Release & Trust<span className="title-dot">.</span></h1>
            <p>Autoritatívny postup pre budúce schválenie je rozdelený na tri nezávislé fázy A → B → C. Táto obrazovka je len zdrojovo overený prehliadač historického návrhu r13; neudeľuje povolenia, neprijíma podpisy a nič nespúšťa.</p>
          </div>
          <div className="section-banner"><Tag kind="hold">PRODUCTION NO-GO</Tag>
            <span>Approval A, B, C: none independently recorded · No active GUI lease · {releaseTrust.phase}</span>
          </div>
          {trustData ? <>
            <div className="metric-grid">
              <Metric label="External approvals" value="0 / 3" desc="A, B and C must be separately accepted" attention/>
              <Metric label="Historical r13 tests" value={trustData.negativeFirstSourceTests} desc="Reported negative-first source tests"/>
              <Metric label="Unresolved NW013 P0" value={trustData.inheritedNW013P0Blockers} desc="Previous production blockers"/>
              <Metric label="Production jobs authorized" value="0" desc="K003 still the only scheduler" attention/>
            </div>
            <GateAReviewPanel evidence={gateAReadOnlyEvidence} />
            <div className="trust-stage-grid">
              {trustData.sequentialStages.map((s,i)=><button key={s.id}
                className={"trust-stage-card "+(reviewStage===s.id?"selected":"")}
                onClick={()=>setReviewStage(s.id)} aria-pressed={reviewStage===s.id}>
                <div className="trust-stage-top"><span>STAGE {s.id}</span><Tag kind="hold">UNAPPROVED</Tag></div>
                <h3>{s.title}</h3>
                <p>{s.requiredEvidence.length} independent evidence items · {s.reviewerRoles.length} reviewer roles</p>
                <small>{i===0?"Trust root required first":i===1?"Requires accepted A":"Requires accepted A and B"}</small>
              </button>)}
            </div>
            {stageSelected && <div className="two-col">
              <Panel eyebrow={"SELECTED STAGE "+stageSelected.id} title={stageSelected.title} extra={<Tag kind="hold">EXTERNAL DECISION MISSING</Tag>}>
                <div className="trust-note">{stageSelected.sourceDescription}</div>
                <div className="detail-section"><label>PREREQUISITES</label>
                  {stageSelected.prerequisiteTokens.length ? stageSelected.prerequisiteTokens.map(p=>
                    <p className="trust-prereq" key={p}>{p} · NOT ACCEPTED</p>) :
                    <p>No earlier stage. Independent external trust must be established first.</p>}
                </div>
                <div className="detail-section"><label>REQUIRED INDEPENDENT REVIEWERS</label>
                  {stageSelected.reviewerRoles.map(role=><p key={role}>{role.replaceAll("_"," ")}</p>)}
                </div>
                <div className="detail-section"><label>ORIGINAL SOURCE REFERENCES</label>
                  {stageSelected.sourceArtifacts.map(ref=><p className="source-path" key={ref}>{ref}</p>)}
                </div>
                <button className="secondary-button" onClick={downloadReviewBrief}>Download unsigned reviewer brief · stage {reviewStage} ↓</button>
              </Panel>
              <Panel eyebrow="EVIDENCE COLLECTION / NO AUTOMATIC APPROVAL" title="Required independent evidence" extra={<Tag kind="pending">{stageSelected.requiredEvidence.length} ITEMS</Tag>}>
                <div className="trust-requirements">{stageSelected.requiredEvidence.map((requirement,i)=>
                  <div className="trust-requirement" key={requirement}>
                    <span>{String(i+1).padStart(2,"0")}</span>
                    <p>{requirement}</p><Tag kind="hold">PENDING</Tag>
                  </div>)}</div>
                <div className="soft-warning">Výber fázy a čítanie dôkazov nie je schválenie. Externý Owner/Witness, podpisy a Windows identita sú naďalej nezávislé požiadavky.</div>
              </Panel>
            </div>}
            <Panel eyebrow="SOURCE AND AUTHORITY SEPARATION" title="Historical r13 security posture" extra={<Tag kind="hold">NO AUTHORITY TRANSFER</Tag>}>
              <div className="three-notes">
                <div><b>K003 only</b><p>One writer per game · max {trustData.executionPolicy.maxGlobalHeavy} global heavy slots · no silent V2→V1 fallback.</p></div>
                <div><b>Source report ≠ live Windows</b><p>Gateway {trustData.executionPolicy.gatewayStateReportedAtSource}, Native Task {trustData.executionPolicy.nativeWorkerStateReportedAtSource}, at recorded {dateDisplay(trustData.sourceDateUtc)}.</p></div>
                <div><b>Explicit external decisions</b><p>Cloud creation, installer, accounts, signing, worker and canary are blocked until separately accepted.</p></div>
              </div>
              <div className="detail-section"><label>OWNER r13 GATE SOURCE SHA-256 · LOCAL INTEGRITY ONLY</label>
                <code>{trustData.pins.reviewGates}</code></div>
              <div className="detail-section"><label>STUDIO PARENT r8 SHA-256</label>
                <code>{trustData.parentR8ZipSha256}</code></div>
              <div className="soft-warning">{trustData.notice}</div>
            </Panel>
          </> : <div className="soft-warning">Review data failed the strict source-bound read-only contract. No external stage, launch, approval or installer status is inferred.</div>}
        </>}
        {page === "settings" && <>
          <div className="page-intro"><div className="eyebrow">MANAGEMENT / SETTINGS</div><h1>Settings<span className="title-dot">.</span></h1><p>Local UI preference preview only. Runtime and protected production settings are not writable from this candidate.</p></div>
          <div className="settings-stack"><Panel eyebrow="GAMING EXPERIENCE" title="Automatic GAME / LIGHT mode"><div className="setting-row"><div><strong>Detect launched games</strong><p>Approved default is enabled; heavy workers should cooperate and release resources during games.</p><Tag kind="pending">LOCAL PREVIEW · NOT APPLIED</Tag></div><button role="switch" aria-checked={gameDraft} className={"toggle " + (gameDraft ? "on":"")} onClick={() => setGameDraft(v => !v)} aria-label="Toggle local preview for automatic gaming mode"><span /></button></div><div className="setting-info">Actual runtime value not queried. This UI-only draft does not change Governor policy.</div></Panel>
          <Panel eyebrow="SECURITY" title="Execution and component policies"><div className="settings-line"><b>Single writer</b><Tag kind="blue">ENFORCED BY DESIGN</Tag></div><div className="settings-line"><b>Maximum concurrent heavy slots</b><strong>{snapshot.policy.maxHeavySlots}</strong></div><div className="settings-line"><b>Unknown result</b><Tag kind="hold">{snapshot.policy.unknownOutcome}</Tag></div><div className="settings-line"><b>Owner / Witness verification</b><Tag kind="hold">DEFERRED</Tag></div><div className="settings-line"><b>Original game resources</b><strong>READ ONLY</strong></div></Panel></div>
        </>}
        <footer className="app-footer"><span>OpenRemaster Studio · isolated UI candidate</span><span>Source-based evidence ≠ production authorization · {snapshot.authority}</span></footer>
      </main>
    </div>
  </div>;
}
