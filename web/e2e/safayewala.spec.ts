import { expect, test } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DATA = path.resolve(__dirname, '../../data')
const sampleText = fs.readFileSync(path.join(DATA, 'Environment_Sample.txt'), 'utf8')
const oursText = fs.readFileSync(path.join(DATA, 'Environment.txt'), 'utf8')
const errorText = fs.readFileSync(path.join(DATA, 'Environment_Error.txt'), 'utf8')

async function skipSplash(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    sessionStorage.setItem('safaye-splash', '1')
  })
}

async function loadSample(page: import('@playwright/test').Page) {
  await page.goto('/')
  // Ensure sidebar visible on narrow viewports
  const toggle = page.getByRole('button', { name: 'Toggle navigation' })
  if (await toggle.isVisible().catch(() => false)) {
    await toggle.click()
  }
  await page.getByRole('button', { name: 'Sample' }).click()
  await expect(
    page.getByText('Environment_Sample.txt', { exact: true }),
  ).toBeVisible({ timeout: 15_000 })
}

test.describe('SafayeWala API (sample data)', () => {
  test('health + backend status', async ({ request }) => {
    const health = await request.get('/api/health')
    expect(health.ok()).toBeTruthy()
    expect(await health.json()).toEqual({ status: 'ok' })

    const status = await request.get('/api/backend-status')
    expect(status.ok()).toBeTruthy()
    const body = await status.json()
    expect(body.csp).toBe(false)
    expect(body.integration).toBe(false)
    expect(body.missing).toEqual(expect.arrayContaining(['csp', 'integration']))
  })

  test('load sample / ours / error environments', async ({ request }) => {
    for (const name of [
      'Environment_Sample.txt',
      'Environment.txt',
      'Environment_Error.txt',
    ]) {
      const res = await request.post('/api/environment/load', { data: { name } })
      expect(res.ok(), name).toBeTruthy()
      const body = await res.json()
      expect(body.grid.rows).toBeGreaterThanOrEqual(8)
      expect(body.rawText).toBeTruthy()
    }

    const err = await request.post('/api/environment/load', {
      data: { name: 'Environment_Error.txt' },
    })
    const errBody = await err.json()
    expect(errBody.unreachable.length).toBeGreaterThanOrEqual(1)
  })

  test('BFS and A* on sample Station→D4 cost 7, A* expands ≤ BFS', async ({
    request,
  }) => {
    const bfs = await request.post('/api/search', {
      data: {
        envText: sampleText,
        start: [0, 0],
        goal: [7, 0],
        algorithm: 'bfs',
      },
    })
    const astar = await request.post('/api/search', {
      data: {
        envText: sampleText,
        start: [0, 0],
        goal: [7, 0],
        algorithm: 'astar',
      },
    })
    expect(bfs.ok()).toBeTruthy()
    expect(astar.ok()).toBeTruthy()
    const b = await bfs.json()
    const a = await astar.json()
    expect(b.found).toBe(true)
    expect(a.found).toBe(true)
    expect(b.cost).toBe(7)
    expect(a.cost).toBe(7)
    expect(a.nodesExpanded).toBeLessThanOrEqual(b.nodesExpanded)
  })

  test('start==goal and unreachable dirty', async ({ request }) => {
    const same = await request.post('/api/search', {
      data: {
        envText: sampleText,
        start: [0, 0],
        goal: [0, 0],
        algorithm: 'bfs',
      },
    })
    const s = await same.json()
    expect(s.found).toBe(true)
    expect(s.cost).toBe(0)
    expect(s.nodesExpanded).toBe(0)

    const unreachable = await request.post('/api/search', {
      data: {
        envText: errorText,
        start: [0, 0],
        goal: [2, 2],
        algorithm: 'bfs',
      },
    })
    expect(unreachable.ok()).toBeTruthy()
    const u = await unreachable.json()
    expect(u.found).toBe(false)
    expect(u.path).toBeNull()
  })

  test('compare returns rows + insight', async ({ request }) => {
    const res = await request.post('/api/compare', {
      data: { envText: sampleText },
    })
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.rows.length).toBeGreaterThan(0)
    expect(body.insight).toMatch(/A\*|BFS|pair/i)
  })

  test('manual mission succeeds; csp mission returns NOT_AVAILABLE', async ({
    request,
  }) => {
    const manual = await request.post('/api/mission/execute', {
      data: {
        envText: sampleText,
        schedule: ['D1', 'D2', 'D3', 'D4'],
        algorithm: 'bfs',
        scheduleSource: 'manual',
      },
    })
    expect(manual.ok()).toBeTruthy()
    const m = await manual.json()
    expect(m.success).toBe(true)
    expect(m.scheduleSource).toBe('manual')
    expect(String(m.message).toUpperCase()).toContain('MANUAL')

    const csp = await request.post('/api/mission/execute', {
      data: {
        envText: sampleText,
        schedule: ['D1'],
        algorithm: 'bfs',
        scheduleSource: 'csp',
      },
    })
    expect(csp.status()).toBe(503)
    expect((await csp.json()).error.code).toBe('INTEGRATION_NOT_AVAILABLE')

    const sched = await request.post('/api/schedule/generate', {
      data: { envText: sampleText, scheduleText: '4\n0\n0\n' },
    })
    expect(sched.status()).toBe(503)
    expect((await sched.json()).error.code).toBe('CSP_NOT_AVAILABLE')
  })

  test('ours environment is searchable', async ({ request }) => {
    const res = await request.post('/api/search', {
      data: {
        envText: oursText,
        start: [0, 0],
        goal: [9, 9],
        algorithm: 'astar',
      },
    })
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.found).toBe(true)
    expect(body.cost).toBeGreaterThan(0)
  })
})

test.describe('SafayeWala UI (Playwright)', () => {
  test.beforeEach(async ({ page }) => {
    await skipSplash(page)
  })

  test('loads app shell and About page', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('SafayeWala').first()).toBeVisible()
    await page.getByRole('link', { name: 'About' }).click()
    await expect(page.getByText('CS-323 Artificial Intelligence')).toBeVisible()
    await expect(page.getByText('How it works')).toBeVisible()
  })

  test('Environment: load Sample shows validation + stats', async ({ page }) => {
    await loadSample(page)
    await expect(page.getByText('coordinates and overlaps')).toBeVisible()
    await expect(page.getByText('all dirty reachable')).toBeVisible()
    await expect(page.getByText('SIZE')).toBeVisible()
  })

  test('Environment: Error case shows unreachable warning', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Error case' }).click()
    await expect(page.getByText(/Unreachable dirty/i)).toBeVisible({
      timeout: 15_000,
    })
  })

  test('Search Lab: BFS Station→D4 shows cost 7', async ({ page }) => {
    await loadSample(page)
    await page.getByRole('link', { name: 'Search Lab' }).click()
    await expect(page.getByRole('button', { name: 'Run' })).toBeVisible()
    await page.getByRole('button', { name: 'bfs', exact: true }).click()
    await page.getByRole('button', { name: 'Run' }).click()

    await expect(page.getByText('COST')).toBeVisible()
    // Cost card value becomes 7
    await expect(page.getByText('7', { exact: true }).first()).toBeVisible({
      timeout: 20_000,
    })
    await expect(page.locator('pre')).toContainText('(0,0)', { timeout: 10_000 })
    await expect(page.locator('pre')).toContainText('(7,0)')
  })

  test('Compare page runs on sample data', async ({ page }) => {
    await loadSample(page)
    await page.getByRole('link', { name: 'Compare' }).click()
    await page.getByRole('button', { name: /Run comparison/i }).click()
    await expect(page.getByText(/Insight/i)).toBeVisible()
    await expect(page.getByText(/successful pair|expanded/i).first()).toBeVisible({
      timeout: 30_000,
    })
    await expect(page.getByRole('cell', { name: 'bfs' }).first()).toBeVisible()
    await expect(page.getByRole('cell', { name: 'astar' }).first()).toBeVisible()
  })

  test('Full Mission: missing-module banner + manual mission', async ({ page }) => {
    await loadSample(page)
    await page.getByRole('link', { name: 'Full Mission' }).click()
    await expect(
      page.getByText(/CSP\/Integration not found yet/i),
    ).toBeVisible()
    await page.getByRole('button', { name: 'Manual demo' }).click()
    await page.getByRole('button', { name: 'Start mission' }).click()
    await expect(page.getByText(/Mission complete|MANUAL DEMO/i).first()).toBeVisible({
      timeout: 30_000,
    })
  })

  test('theme toggle flips html.light class', async ({ page }) => {
    await page.goto('/')
    const toggle = page.getByRole('button', { name: 'Toggle navigation' })
    if (await toggle.isVisible().catch(() => false)) {
      await toggle.click()
    }
    const html = page.locator('html')
    const themeBtn = page.getByRole('button', { name: 'Toggle theme' })
    await expect(themeBtn).toBeVisible({ timeout: 10_000 })
    const beforeLight = await html.evaluate((el) => el.classList.contains('light'))
    await themeBtn.click()
    await expect
      .poll(async () => html.evaluate((el) => el.classList.contains('light')))
      .not.toBe(beforeLight)
  })
})
