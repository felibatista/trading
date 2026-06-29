import { afterEach, expect, test, vi } from 'vitest'
import { api } from './api'

afterEach(() => vi.restoreAllMocks())

function mockFetch(captured: string[]) {
  vi.stubGlobal('fetch', (url: string) => {
    captured.push(url)
    return Promise.resolve({ ok: true, json: () => Promise.resolve([]) } as Response)
  })
}

test('getStatus adds account query', async () => {
  const urls: string[] = []
  mockFetch(urls)
  await api.getStatus('scalper')
  expect(urls[0]).toContain('/api/status?account=scalper')
})

test('getCandles keeps limit and adds account', async () => {
  const urls: string[] = []
  mockFetch(urls)
  await api.getCandles(undefined, undefined, 50, 'momentum')
  expect(urls[0]).toContain('limit=50')
  expect(urls[0]).toContain('account=momentum')
})

test('getAccounts hits /api/accounts', async () => {
  const urls: string[] = []
  mockFetch(urls)
  await api.getAccounts()
  expect(urls[0]).toContain('/api/accounts')
})
