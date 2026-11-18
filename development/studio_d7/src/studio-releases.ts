import {readStoredResponse} from './stored-json';

export const repository = 'https://github.com/semishsvk/OpenRemaster-Framework';
export const releasesEndpoint = 'https://api.github.com/repos/semishsvk/OpenRemaster-Framework/releases?per_page=5';
export type StudioRelease = {tag: string; commit: string; published: string; notes: string; page: string; file: string; download: string; digest: string | null; runId: string | null};
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid release metadata');
  return value as Record<string, unknown>;
}
function string(value: unknown, max: number): string {
  if (typeof value !== 'string' || value.length > max) throw Error('Invalid release field');
  return value;
}
export function parseStudioReleases(raw: unknown): StudioRelease[] {
  if (!Array.isArray(raw) || raw.length > 5) throw Error('Invalid release list');
  const releases: StudioRelease[] = [];
  for (const item of raw) {
    const value = object(item);
    if (value.draft !== false || value.prerelease !== true || typeof value.tag_name !== 'string' || !value.tag_name.startsWith('studio-dev-')) continue;
    const tag = string(value.tag_name, 160), commit = string(value.target_commitish, 40);
    const match = /^studio-dev-([a-f0-9]{12}|[a-f0-9]{40})(?:-([0-9]{1,20})-([0-9]{1,6}))?$/.exec(tag);
    if (!match || !/^[a-f0-9]{40}$/.test(commit) || !commit.startsWith(match[1])) throw Error('Release source identity was rejected');
    const published = string(value.published_at, 40);
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(published) || !Number.isFinite(Date.parse(published))) throw Error('Invalid release date');
    if (value.html_url !== `${repository}/releases/tag/${tag}`) throw Error('Release page was rejected');
    if (!Array.isArray(value.assets) || value.assets.length > 20) throw Error('Invalid release assets');
    const expectedName = `OpenRemaster-Studio-DEV-windows-x64-${commit.slice(0,12)}.zip`;
    const matches = value.assets.map(object).filter(asset => asset.name === expectedName);
    if (matches.length !== 1) continue;
    const asset = matches[0], download = `${repository}/releases/download/${tag}/${expectedName}`;
    if (asset.browser_download_url !== download || !Number.isSafeInteger(asset.size) || Number(asset.size) < 1 || Number(asset.size) > 134217728) throw Error('Release download was rejected');
    const digest = asset.digest === null || asset.digest === undefined ? null : string(asset.digest, 71);
    if (digest !== null && !/^sha256:[a-f0-9]{64}$/.test(digest)) throw Error('Release checksum was rejected');
    const notes = value.body === null ? '' : string(value.body, 20000);
    const legacyRun = notes.match(/https:\/\/github\.com\/semishsvk\/OpenRemaster-Framework\/actions\/runs\/([0-9]{1,20})(?![0-9])/);
    releases.push({tag, commit, published, notes, page: value.html_url as string, file: expectedName, download, digest: digest?.slice(7) ?? null, runId: match[2] ?? legacyRun?.[1] ?? null});
  }
  if (new Set(releases.map(release => release.tag)).size !== releases.length) throw Error('Duplicate releases');
  return releases.sort((a,b) => b.published.localeCompare(a.published));
}
export async function fetchReleaseJson(url: string, signal: AbortSignal): Promise<unknown> {
  return readStoredResponse(await fetch(url, {signal, credentials:'omit', redirect:'error', cache:'no-store', headers:{Accept:'application/json'}}), 131072, signal);
}
export function parseReleaseCi(raw: unknown, release: StudioRelease): string {
  const value = object(raw);
  if (String(value.id) !== release.runId || value.head_sha !== release.commit
      || value.event !== 'push' || value.path !== '.github/workflows/studio-windows-dev.yml') throw Error('CI source binding was rejected');
  if (value.status !== 'completed') return 'CI is still running';
  return value.conclusion === 'success' ? 'CI passed for this source commit' : 'CI did not pass for this source commit';
}
export async function verifyReleaseFile(file: File, expected: string): Promise<string> {
  if (!/^[a-f0-9]{64}$/.test(expected) || file.size < 1 || file.size > 134217728) throw Error('Select a ZIP smaller than 128 MiB');
  const bytes = new Uint8Array(await crypto.subtle.digest('SHA-256', await file.arrayBuffer()));
  const actual = Array.from(bytes, byte => byte.toString(16).padStart(2,'0')).join('');
  if (actual !== expected) throw Error(`Checksum mismatch. Observed SHA-256 ${actual}`);
  return actual;
}
