import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  fetchPapers, fetchPaperStats, fetchPipelineRuns, fetchReports,
  fetchReport, searchPapers, runPipeline, generateReport,
} from '../../data/api'

const CACHE_PREFIX = 'ar_cache:'

describe('apiFetch wrappers', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  async function mockFetch(status: number, body: unknown) {
    const fetchMock = vi.mocked(globalThis.fetch)
    fetchMock.mockResolvedValueOnce({
      ok: status >= 200 && status < 300,
      status,
      statusText: status === 200 ? 'OK' : 'Error',
      text: async () => JSON.stringify(body),
      json: async () => body,
    } as Response)
  }

  it('fetchPapers builds query string correctly', async () => {
    await mockFetch(200, { total: 1, results: [] })
    const res = await fetchPapers('general_ai', 2, 10, 'transformer')
    expect(res.fromCache).toBe(false)
    expect(res.data).toEqual({ total: 1, results: [] })
    const fetchMock = vi.mocked(globalThis.fetch)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const url = fetchMock.mock.calls[0][0] as string
    expect(url).toContain('/papers?')
    expect(url).toContain('bucket=general_ai')
    expect(url).toContain('page=2')
    expect(url).toContain('limit=10')
    expect(url).toContain('search=transformer')
  })

  it('fetchPapers omits optional params', async () => {
    await mockFetch(200, { total: 0, results: [] })
    const res = await fetchPapers()
    expect(res.fromCache).toBe(false)
    const fetchMock = vi.mocked(globalThis.fetch)
    const url = fetchMock.mock.calls[0][0] as string
    expect(url).not.toContain('bucket=')
    expect(url).not.toContain('search=')
    expect(url).toContain('page=1')
    expect(url).toContain('limit=50')
  })

  it('fetchPaperStats calls /papers/stats', async () => {
    const body = { total: 5, today: 1, per_bucket: {}, per_date: [] }
    await mockFetch(200, body)
    const res = await fetchPaperStats()
    expect(res.data.total).toBe(5)
    expect(res.fromCache).toBe(false)
    const fetchMock = vi.mocked(globalThis.fetch)
    expect(fetchMock.mock.calls[0][0]).toContain('/papers/stats')
  })

  it('fetchPipelineRuns appends limit', async () => {
    await mockFetch(200, [])
    const res = await fetchPipelineRuns(10)
    expect(res.fromCache).toBe(false)
    expect(res.data).toEqual([])
    const fetchMock = vi.mocked(globalThis.fetch)
    expect(fetchMock.mock.calls[0][0]).toContain('/pipeline-runs?limit=10')
  })

  it('fetchReports calls /reports', async () => {
    await mockFetch(200, [])
    const res = await fetchReports()
    expect(res.fromCache).toBe(false)
    const fetchMock = vi.mocked(globalThis.fetch)
    expect(fetchMock.mock.calls[0][0]).toContain('/reports')
  })

  it('fetchReport interpolates id', async () => {
    const body = { id: 7, period: '7d', generated_at: '', paper_count: 1, content_html: '' }
    await mockFetch(200, body)
    const res = await fetchReport(7)
    expect(res.data.id).toBe(7)
    const fetchMock = vi.mocked(globalThis.fetch)
    expect(fetchMock.mock.calls[0][0]).toContain('/reports/7')
  })

  it('searchPapers encodes query', async () => {
    await mockFetch(200, { query: 'foo bar', results: [] })
    const res = await searchPapers('foo bar', 5)
    expect(res.fromCache).toBe(false)
    const fetchMock = vi.mocked(globalThis.fetch)
    expect(fetchMock.mock.calls[0][0]).toContain('/search?q=foo%20bar')
    expect(fetchMock.mock.calls[0][0]).toContain('limit=5')
  })

  it('runPipeline POSTs /ingest', async () => {
    await mockFetch(200, { status: 'ok', paper_count: 3, stages: {} })
    const res = await runPipeline()
    expect(res.status).toBe('ok')
    const fetchMock = vi.mocked(globalThis.fetch)
    expect(fetchMock.mock.calls[0][1]?.method).toBe('POST')
    expect(fetchMock.mock.calls[0][0]).toContain('/ingest')
  })

  it('generateReport POSTs with period', async () => {
    await mockFetch(200, { id: 1, period: '1m', paper_count: 6 })
    const res = await generateReport('1m')
    expect(res.id).toBe(1)
    const fetchMock = vi.mocked(globalThis.fetch)
    expect(fetchMock.mock.calls[0][1]?.method).toBe('POST')
    expect(fetchMock.mock.calls[0][0]).toContain('/reports/generate?period=1m')
  })

  it('throws on non-ok response with no cache', async () => {
    await mockFetch(500, 'Internal Server Error')
    await expect(fetchPaperStats()).rejects.toThrow('API 500:')
  })

  it('sets default headers', async () => {
    await mockFetch(200, { total: 0, today: 0, per_bucket: {}, per_date: [] })
    await fetchPaperStats()
    const fetchMock = vi.mocked(globalThis.fetch)
    const init = fetchMock.mock.calls[0][1] as RequestInit
    expect(init.headers).toMatchObject({
      'Content-Type': 'application/json',
      'ngrok-skip-browser-warning': '1',
    })
  })
})

describe('API caching', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  async function mockFetch(status: number, body: unknown) {
    const fetchMock = vi.mocked(globalThis.fetch)
    fetchMock.mockResolvedValueOnce({
      ok: status >= 200 && status < 300,
      status,
      statusText: status === 200 ? 'OK' : 'Error',
      text: async () => JSON.stringify(body),
      json: async () => body,
    } as Response)
  }

  function mockNetworkError() {
    const fetchMock = vi.mocked(globalThis.fetch)
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))
  }

  function mockServerError(status: number, body: string) {
    const fetchMock = vi.mocked(globalThis.fetch)
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status,
      statusText: 'Error',
      text: async () => body,
      json: async () => { throw new Error('not json'); },
    } as Response)
  }

  it('caches successful responses to localStorage', async () => {
    const body = { total: 5, today: 1, per_bucket: {}, per_date: [] }
    await mockFetch(200, body)
    const res = await fetchPaperStats()
    expect(res.fromCache).toBe(false)
    expect(res.data).toEqual(body)
    expect(JSON.parse(localStorage.getItem(CACHE_PREFIX + 'paper_stats')!)).toEqual(body)
  })

  it('returns cached data on network failure', async () => {
    const body = { total: 42, today: 3, per_bucket: { general_ai: 20 }, per_date: [] }
    await mockFetch(200, body)
    const first = await fetchPaperStats()
    expect(first.fromCache).toBe(false)

    mockNetworkError()
    const second = await fetchPaperStats()
    expect(second.fromCache).toBe(true)
    expect(second.data).toEqual(body)
  })

  it('returns cached data on 5xx server error', async () => {
    const body = { total: 10, today: 0, per_bucket: {}, per_date: [] }
    await mockFetch(200, body)
    await fetchPaperStats()

    mockServerError(500, 'Internal Server Error')
    const res = await fetchPaperStats()
    expect(res.fromCache).toBe(true)
    expect(res.data.total).toBe(10)
  })

  it('throws when there is no cache and network fails', async () => {
    mockNetworkError()
    await expect(fetchPaperStats()).rejects.toThrow('Failed to fetch')
  })

  it('4xx errors are NOT treated as offline (no cache fallback)', async () => {
    const fetchMock = vi.mocked(globalThis.fetch)
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      text: async () => 'Not Found',
      json: async () => { throw new Error('not json'); },
    } as Response)

    await expect(fetchReport(9999)).rejects.toThrow('API 404')
  })

  it('POST endpoints never cache', async () => {
    await mockFetch(200, { status: 'ok', paper_count: 1, stages: {} })
    await runPipeline()
    expect(localStorage.getItem(CACHE_PREFIX + 'ingest')).toBeNull()
  })
})