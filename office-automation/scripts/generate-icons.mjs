// Creates the PNG app icons (used when installing the app) from public/favicon.svg.
// Run with:  node scripts/generate-icons.mjs
// Needs Playwright with Chromium installed (npx playwright install chromium).
import { readFile, writeFile } from 'node:fs/promises'
import { chromium } from 'playwright'

const svg = await readFile(new URL('../public/favicon.svg', import.meta.url), 'utf8')
const svgData = `data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}`

const targets = [
  { file: 'pwa-192x192.png', size: 192, padding: 0, bg: 'transparent' },
  { file: 'pwa-512x512.png', size: 512, padding: 0, bg: 'transparent' },
  // Maskable icons need a "safe zone": Android may crop the edges into a circle.
  { file: 'pwa-maskable-512x512.png', size: 512, padding: 0.12, bg: '#1e40af' },
  { file: 'apple-touch-icon.png', size: 180, padding: 0.06, bg: '#1e40af' },
]

const browser = await chromium.launch()
const page = await browser.newPage()
for (const t of targets) {
  const inner = Math.round(t.size * (1 - t.padding * 2))
  await page.setViewportSize({ width: t.size, height: t.size })
  await page.setContent(
    `<html><body style="margin:0;background:${t.bg};display:grid;place-items:center;width:${t.size}px;height:${t.size}px">
       <img src="${svgData}" width="${inner}" height="${inner}"/>
     </body></html>`,
  )
  const png = await page.screenshot({ omitBackground: t.bg === 'transparent' })
  await writeFile(new URL(`../public/${t.file}`, import.meta.url), png)
  console.log('created public/' + t.file)
}
await browser.close()
