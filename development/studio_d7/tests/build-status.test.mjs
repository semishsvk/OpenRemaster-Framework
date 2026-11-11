import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {existsSync, readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import test from 'node:test';
import {createElement} from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import ts from 'typescript';
import {createServer} from 'vite';

const require = createRequire(import.meta.url);
const src = new URL('../src/', import.meta.url);
const loadCache = new Map();

function loadSource(url) {
  if (loadCache.has(url.href)) return loadCache.get(url.href);
  const source = readFileSync(url, 'utf8');
  if (url.pathname.endsWith('.json')) return JSON.parse(source);
  const {outputText} = ts.transpileModule(source, {compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    jsx: ts.JsxEmit.ReactJSX,
    esModuleInterop: true,
  }});
  const module = {exports: {}};
  loadCache.set(url.href, module.exports);
  new Function('require', 'module', 'exports', outputText)(specifier => {
    if (!specifier.startsWith('.')) return require(specifier);
    const resolved = ['', '.ts', '.tsx'].map(extension => new URL(specifier + extension, url))
      .find(candidate => existsSync(candidate));
    if (!resolved) throw new Error(`Cannot resolve ${specifier} from ${url.href}`);
    return loadSource(resolved);
  }, module, module.exports);
  loadCache.set(url.href, module.exports);
  return module.exports;
}

const {OpenAzraelBuildReview} = loadSource(new URL('OpenAzraelBuildReview.tsx', src));
const render = projectId => renderToStaticMarkup(createElement(OpenAzraelBuildReview, {projects: [{id: projectId}]}));

test('archived report bytes match the displayed project provenance', () => {
  const file = readFileSync(new URL('data/openazrael-candidate-v205-iter2-acceptance.json', src));
  const report = JSON.parse(file);
  const markup = render('OpenAzrael');
  assert.ok(markup.includes(report.candidate));
  assert.ok(markup.includes(createHash('sha256').update(file).digest('hex')));
});

test('OpenAzrael shows archived passes and explicit fidelity gaps under HOLD', () => {
  const markup = render('OpenAzrael');
  assert.match(markup, /<summary>OpenAzrael build review<\/summary>/);
  assert.match(markup, /Build status.*?HOLD.*?candidate-v205-iter2/);
  assert.match(markup, /Save compatibility<\/dt><dd>PASS \(reported test v150\)/);
  assert.match(markup, /Clean install startup<\/dt><dd>PASS/);
  assert.match(markup, /canonical paired original-runtime visual FidelityBundle/);
  assert.match(markup, /ACCEPTANCE\.json/);
});

test('README check records the package observation and its build identity', () => {
  const check = loadSource(new URL('data/openazrael-candidate-v205-iter2-readme-check.json', src));
  const file = readFileSync(new URL('data/openazrael-candidate-v205-iter2-acceptance.json', src));
  assert.equal(check.projectId, 'OpenAzrael');
  assert.equal(check.buildId, JSON.parse(file).candidate);
  assert.equal(check.acceptanceSha256, createHash('sha256').update(file).digest('hex'));
  assert.ok(Number.isFinite(Date.parse(check.checkedAt)));
  const markup = render('OpenAzrael');
  assert.match(markup, /Build README<\/dt><dd>README_HOLD/);
  assert.match(markup, /README\.md missing/);
  assert.match(markup, /Archived package checked <time/);
  assert.match(markup, /verify_dev_build_readme\.py/);
});

test('v250 details use their own package report, checksums and README observation', () => {
  const report = loadSource(new URL('data/openazrael-v250-build.json', src));
  const check = loadSource(new URL('data/openazrael-v250-readme-check.json', src));
  const readme = readFileSync(new URL('../evidence/OpenAzrael-v250-README.txt', import.meta.url));
  const manifest = readFileSync(new URL('../evidence/OpenAzrael-v250-SHA256SUMS.txt', import.meta.url));
  assert.equal(report.sourceSha256, createHash('sha256').update(readme).digest('hex'));
  assert.equal(report.packageManifestSha256, createHash('sha256').update(manifest).digest('hex'));
  assert.ok(manifest.toString().includes(`${report.sourceSha256}  README.txt`));
  assert.equal(check.packageManifestSha256, report.packageManifestSha256);
  assert.equal(check.projectId, report.projectId);
  assert.equal(check.buildId, report.buildId);
  assert.ok(Number.isFinite(Date.parse(check.checkedAt)));
  const lines = readme.toString().split(/\r?\n/);
  for (const value of report.checks) assert.ok(lines.includes(value), value);
  for (const value of report.fidelityGaps) assert.ok(lines.includes(`- ${value}`), value);

  const markup = render('OpenAzrael');
  const groups = [...markup.matchAll(/<details name="([^"]+)"( open="")?><summary>([^<]+)<\/summary>/g)];
  assert.deepEqual(groups.map(match => match[3]), ['candidate-v205-iter2', 'OpenAzrael-v250']);
  assert.equal(groups[0][1], groups[1][1]);
  assert.ok(groups[0][2]);
  assert.equal(groups[1][2], undefined);
  const older = markup.slice(groups[0].index, groups[1].index);
  const newer = markup.slice(groups[1].index, markup.indexOf('<summary>Compare reported checks'));
  assert.doesNotMatch(older, /Graphics mode 12\/12 PASS/);
  assert.doesNotMatch(newer, /reported test v150/);
  assert.match(newer, /README_HOLD.*README\.md missing.*README\.txt.*Graphics mode 12\/12 PASS/);
});

test('comparison pairs archived results by check and keeps their source detail', () => {
  const table = render('OpenAzrael').match(/<table class="build-check-comparison">.*?<\/table>/)?.[0];
  assert.ok(table);
  assert.match(table, /<th scope="col">candidate-v205-iter2<\/th><th scope="col">OpenAzrael-v250<\/th>/);
  assert.match(table, /<th scope="row">Save compatibility<\/th><td>PASS \(reported test v150\)<\/td><td>37\/37 PASS<\/td>/);
  assert.match(table, /<th scope="row">Room transitions<\/th><td>PASS \(reported test v205\)<\/td><td>109\/109 PASS<\/td>/);
  assert.equal([...table.matchAll(/scope="row"/g)].length, 6);
  assert.doesNotMatch(render('OpenAzrael-Retail'), /build-check-comparison/);
});

test('R1 scene comparison embeds the two exact captures and keeps their fidelity hold', () => {
  const markup = render('OpenAzrael');
  const captures = [...markup.matchAll(/src="\.\/fidelity\/openazrael-r1\/([^"/]+\.png)"/g)];
  assert.deepEqual(captures.map(match => match[1]), ['original-r1083.png', 'remaster-r1073.png']);
  for (const [, file] of captures) {
    const bytes = readFileSync(new URL(`../public/fidelity/openazrael-r1/${file}`, import.meta.url));
    assert.equal(bytes.toString('ascii', 12, 16), 'IHDR');
    assert.deepEqual([bytes.readUInt32BE(16), bytes.readUInt32BE(20)], [640, 480]);
    assert.ok(markup.includes(createHash('sha256').update(bytes).digest('hex')));
  }
  assert.match(markup, /FIDELITY HOLD.*?Camera position and HUD phase were only partially synchronized/);
  assert.doesNotMatch(render('OpenAzrael-Retail'), /Compare R1 corridor captures/);
});

test('archived passes do not imply freshness or fill in unrecorded metadata', () => {
  const markup = render('OpenAzrael');
  assert.match(markup, /Historical snapshot\. Current build status is unknown/);
  assert.match(markup, /Exact edition unrecorded/);
  assert.match(markup, /Verification time<\/dt><dd>Unrecorded/);
});

test('other projects and unknown scopes cannot display OpenAzrael evidence', () => {
  for (const project of ['OpenZak', 'OpenAzrael-Retail', 'unknown']) {
    assert.equal(render(project), '');
  }
});

test('the existing Projects route shows the review and the existing project cards', async () => {
  const vite = await createServer({server: {middlewareMode: true, ws: false}, appType: 'custom', logLevel: 'silent'});
  try {
    const {default: App} = await vite.ssrLoadModule('/src/App.tsx');
    globalThis.window = {location: {hash: '#projects'}};
    const markup = renderToStaticMarkup(createElement(App));
    assert.match(markup, /Project Workbench/);
    assert.match(markup, /OpenAzrael build review/);
    assert.match(markup, /Compare R1 corridor captures/);
    assert.match(markup, /class="project-card"/);
    globalThis.window.location.hash = '#overview';
    assert.doesNotMatch(renderToStaticMarkup(createElement(App)), /OpenAzrael build review/);
  } finally {
    delete globalThis.window;
    await vite.close();
  }
});
