import fs from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { chromium } from 'playwright';
import axeSource from 'axe-core/axe.min.js';

const baseUrl = process.env.FACEATTEND_BASE_URL || 'http://localhost:8080';
const outputDir = path.resolve('tools/screenshots');
const pages = [
  ['landing', '/'],
  ['dashboard', '/dashboard'],
];
const viewports = [
  ['desktop', { width: 1366, height: 768 }],
  ['mobile', { width: 390, height: 844 }],
];
const themes = ['light', 'dark'];

await fs.mkdir(outputDir, { recursive: true });
const browser = await chromium.launch();
const results = [];

try {
  for (const [pageName, route] of pages) {
    for (const theme of themes) {
      for (const [viewportName, viewport] of viewports) {
        const page = await browser.newPage({ viewport, colorScheme: theme });
        const url = new URL(route, baseUrl);
        url.searchParams.set('theme-audit', theme);
        await page.goto(url, { waitUntil: 'networkidle' });
        await page.evaluate((selectedTheme) => {
          document.documentElement.dataset.themePreference = selectedTheme;
          document.documentElement.dataset.theme = selectedTheme;
        }, theme);
        await page.waitForTimeout(150);
        const screenshot = path.join(outputDir, `${pageName}-${theme}-${viewportName}.png`);
        await page.screenshot({ path: screenshot, fullPage: true });
        await page.addScriptTag({ content: axeSource });
        const axe = await page.evaluate(async () => window.axe.run(document, {
          runOnly: ['cat.color'],
        }));
        results.push({
          page: pageName,
          theme,
          viewport: viewportName,
          screenshot,
          violations: axe.violations.map(({ id, help, nodes }) => ({
            id,
            help,
            nodes: nodes.length,
          })),
        });
        await page.close();
      }
    }
  }
} finally {
  await browser.close();
}

console.log(JSON.stringify(results, null, 2));
if (results.some(({ violations }) => violations.length > 0)) {
  process.exitCode = 1;
}
