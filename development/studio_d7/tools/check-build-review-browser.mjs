import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';
import {createRequire} from 'node:module';
import {resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';

const require = createRequire(import.meta.url);
const {chromium} = require(process.env.STUDIO_PLAYWRIGHT || 'playwright');
const dist = fileURLToPath(new URL('../dist/', import.meta.url));
const origin = 'http://studio.test';
const browser = await chromium.launch({
  executablePath: process.env.STUDIO_BROWSER || undefined,
  chromiumSandbox: true,
  headless: true,
  timeout: 15000,
  args: ['--disable-background-networking', '--disable-component-update'],
});

try {
  for (const viewport of [{width: 1280, height: 800}, {width: 390, height: 844}]) {
    const context = await browser.newContext({viewport, offline: true, serviceWorkers: 'block'});
    try {
      const unexpected = [];
      await context.route('**/*', async route => {
        const url = new URL(route.request().url());
        const path = decodeURIComponent(url.pathname === '/' ? '/index.html' : url.pathname);
        const file = resolve(dist, `.${path}`);
        if (url.origin === origin && file.startsWith(`${resolve(dist)}${sep}`) && existsSync(file)) {
          await route.fulfill({path: file});
        } else {
          unexpected.push(url.href);
          await route.abort();
        }
      });
      const page = await context.newPage();
      page.setDefaultTimeout(5000);
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(`${origin}/#projects`);
      await page.getByRole('heading', {name: /^Project Workbench/}).waitFor();
      await page.locator('.project-card').filter({has: page.getByRole('heading', {name: 'OpenAzrael', exact: true})}).waitFor();
      const panel = page.getByRole('region', {name: 'Build status', exact: true});
      assert.equal(await panel.isVisible(), false);
      await page.getByText('OpenAzrael build review', {exact: true}).focus();
      await page.keyboard.press('Enter');
      await panel.waitFor();

      const oldBuild = panel.locator('details[name]').filter({hasText: 'candidate-v205-iter2'});
      const newBuild = panel.locator('details[name]').filter({hasText: 'OpenAzrael-v250'});
      await oldBuild.getByText('README.md missing', {exact: true}).waitFor();
      await newBuild.locator(':scope > summary').click();
      await newBuild.getByText('README.md missing', {exact: true}).waitFor();
      assert.equal(await oldBuild.getByText('README.md missing', {exact: true}).isVisible(), false);
      await panel.getByText('Compare reported checks', {exact: true}).click();
      const comparison = panel.getByRole('table', {name: 'Archived check comparison'});
      const save = comparison.getByRole('row').filter({has: page.getByRole('rowheader', {name: 'Save compatibility'})});
      assert.deepEqual(await save.getByRole('cell').allTextContents(), ['PASS (reported test v150)', '37/37 PASS']);
      assert.equal(await panel.evaluate(element => element.scrollWidth <= element.clientWidth + 1), true);

      const scene = page.getByRole('region', {name: 'Original and remaster scene comparison'});
      await scene.getByText('Compare R1 corridor captures', {exact: true}).click();
      const images = await scene.getByRole('img').all();
      assert.equal(images.length, 2);
      for (const image of images) {
        await image.scrollIntoViewIfNeeded();
        await image.evaluate(element => element.decode());
        assert.deepEqual(await image.evaluate(element => [element.naturalWidth, element.naturalHeight]), [640, 480]);
      }
      const [original, remaster] = await Promise.all(images.map(image => image.boundingBox()));
      assert.ok(viewport.width > 640 ? remaster.x > original.x && remaster.y === original.y : remaster.y > original.y && remaster.x === original.x);
      await page.goto(`${origin}/#overview`);
      await panel.waitFor({state: 'detached'});
      assert.deepEqual(errors, []);
      assert.deepEqual(unexpected, []);
      console.log(`PASS ${viewport.width}x${viewport.height}: Projects, keyboard, build comparison and R1 captures`);
    } finally {
      await context.close();
    }
  }
} finally {
  await browser.close();
}
