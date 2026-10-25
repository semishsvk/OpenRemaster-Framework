/** Imported snapshots are display data and never grant authority. */
type Obj = Record<string, unknown>;
const object = (v: unknown): v is Obj => v !== null && typeof v === 'object' && !Array.isArray(v);
const text = (v: unknown) => typeof v === 'string' && v.length <= 4096;
const hash = (v: unknown) => v === null || typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
const equal = (a: unknown, b: unknown): boolean => {
  if (object(a) && object(b)) return keys(a,b) && Object.keys(b).every(k => equal(a[k],b[k]));
  return a === b;
};
const keys = (a: Obj, b: Obj) => Object.keys(a).length === Object.keys(b).length && Object.keys(b).every(k => Object.hasOwn(a,k));
function record(value: unknown, template: Obj): value is Obj {
  if (!object(value) || !keys(value,template)) return false;
  return Object.keys(template).every(k => {
    const v=value[k], t=template[k];
    if (k.endsWith('Sha256')) return hash(v);
    if (k==='testsPerPlatform') return v===null || typeof v==='number' && Number.isSafeInteger(v) && v>=0;
    if (k==='checkpointRel' || k==='sourceRel') return v===null || text(v);
    if (typeof t==='string') return text(v);
    if (typeof t==='boolean') return typeof v==='boolean';
    return false;
  });
}
export function validateSnapshot(value: unknown, baseline: unknown): boolean {
  if (!object(value) || !object(baseline) || !keys(value,baseline)) return false;
  for (const k of ['schema','captureMethod','authority']) if (value[k]!==baseline[k]) return false;
  if (!text(value.host) || !text(value.generatedUtc) || typeof value.generatedUtc!=='string' || !Number.isFinite(Date.parse(value.generatedUtc))) return false;
  if (!equal(value.production,baseline.production) || !equal(value.policy,baseline.policy)) return false;
  if (!object(value.packaging) || !object(baseline.packaging) || !keys(value.packaging,baseline.packaging)) return false;
  const p=value.packaging,b=baseline.packaging;
  for (const k of ['status','installerAccepted','approvedIconLocated']) if (p[k]!==b[k]) return false;
  if (!hash(p.planSha256) || !text(p.plannedSetup) || !text(p.targetApp)) return false;
  if (!Array.isArray(p.components) || !Array.isArray(b.components) || p.components.length!==b.components.length) return false;
  const seenComponents=new Set();
  for (const c of p.components) {
    if (!object(c) || typeof c.id!=='string' || seenComponents.has(c.id)) return false;
    const original=b.components.find(item=>object(item) && item.id===c.id);
    if (!original || !equal(c,original)) return false;
    seenComponents.add(c.id);
  }
  if (!Array.isArray(value.modules) || !Array.isArray(baseline.modules) || value.modules.length!==baseline.modules.length) return false;
  const seen=new Set(),maturities=new Set(['SHADOW_PASS','SOFTWARE_TESTED','HOLD','RESEARCH','UNRESOLVED','DESIGN','MISSING']);
  for (const module of value.modules) {
    if (!object(module) || typeof module.id!=='string' || seen.has(module.id)) return false;
    const original=baseline.modules.find(item=>object(item) && item.id===module.id);
    if (!object(original) || !record(module,original) || module.productionAdmitted!==false || !maturities.has(module.maturity as string)) return false;
    seen.add(module.id);
  }
  if (!Array.isArray(value.projects) || value.projects.length>128) return false;
  const projects=new Set();
  for (const project of value.projects) {
    if (!object(project) || !keys(project,{id:'',type:'',runtime:''}) || !text(project.id) || !text(project.type) || !text(project.runtime) || projects.has(project.id)) return false;
    projects.add(project.id);
  }
  return true;
}
