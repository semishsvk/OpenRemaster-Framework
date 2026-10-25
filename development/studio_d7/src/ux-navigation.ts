// Isolated typed adapter for Studio React integration. No mutation or dispatch.
export type PrimaryArea='overview'|'projects'|'workflows'|'validation'|'knowledge'|'system';
export const GROUPS:readonly PrimaryArea[]=['overview','projects','workflows','validation','knowledge','system'];
export const LEGACY_ROUTES={
 overview:['overview'],projects:['projects','completion'],workflows:['nexttask'],
 validation:['fidelity','inspector','replay','evidence'],knowledge:['assets','intelligence','localization'],
 system:['modules','buildlab','native','portable','runtime','security','crossplane','architecture','governor','components','compat','trust','settings']
} as const;
export type LegacyRoute=(typeof LEGACY_ROUTES)[keyof typeof LEGACY_ROUTES][number];
export const labels:Record<PrimaryArea,string>={overview:'Overview',projects:'Projects',workflows:'Workflows',validation:'Validation',knowledge:'Knowledge',system:'System'};
export function groupFor(route:string):PrimaryArea{
 for(const group of GROUPS) if((LEGACY_ROUTES[group] as readonly string[]).includes(route))return group;
 return 'overview';
}
export function groupLinks(group:PrimaryArea):readonly string[]{return LEGACY_ROUTES[group];}
export function isLegacyRoute(value:string):value is LegacyRoute{return GROUPS.some(g=>(LEGACY_ROUTES[g] as readonly string[]).includes(value));}
