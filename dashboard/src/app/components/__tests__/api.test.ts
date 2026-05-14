import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  fetchPapers, fetchPaperStats, fetchPipelineRuns, fetchReports,
  fetchReport, searchPapers, runPipeline, generateReport,
} from '../../data/api'

describe('apiFetch wrappers', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
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
    await fetchPapers('general_ai', 2, 10, 'transformer')
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
    await fetchPapers()
    const fetchMock = vi.mocked(globalThis.fetch)
    const url = fetchMock.mock.calls[0][0] as string
    expect(url).not.toContain('bucket=')
    expect(url).not.toContain('search=')
    expect(url).toContain('page=1')
    expect(url).toContain('limit=50')
  })

  it('fetchPaperStats calls /papers/stats', async () => {
    await mockFetch(200, { total: 5, today: 1, per_bucket: {}, per_date: [] })
    const result = await fetchPaperStats()
    expect(result.total).toBe(5)
    const fetchMock = vi.mocked(globalThis.fetch)
    expect(fetchMock.mock.calls[0][0]).toContain('/papers/stats')
  })

  it('fetchPipelineRuns appends limit', async () => {
    await mockFetch(200, [])
    await fetchPipelineRuns(10)
    const fetchMock = vi.mocked(globalThis.fetch)
    expect(fetchMock.mock.calls[0][0]).toContain('/pipeline-runs?limit=10')
  })

  it('fetchReports calls /reports', async () => {
    await mockFetch(200, [])
    await fetchReports()
    const fetchMock = vi.mocked(globalThis.fetch)
    expect(fetchMock.mock.calls[0][0]).toContain('/reports')
  })

  it('fetchReport interpolates id', async () => {
    await mockFetch(200, { id: 7, period: '7d', generated_at: '', paper_count: 1, content_html: '' })
    await fetchReport(7)
    const fetchMock = vi.mocked(globalThis.fetch)
    expect(fetchMock.mock.calls[0][0]).toContain('/reports/7')
  })

  it('searchPapers encodes query', async () => {
    await mockFetch(200, { query: 'foo bar', results: [] })
    await searchPapers('foo bar', 5)
    const fetchMock = vi.mocked(globalThis.fetch)
    expect(fetchMock.mock.calls[0][0]).toContain('/search?q=foo%20bar')
    expect(fetchMock.mock.calls[0][0]).toContain('limit=5')
  })

  it('runPipeline POSTs /ingest', async () => {
    await mockFetch(200, { status: 'ok', paper_count: 3, stages: {} })
    await runPipeline()
    const fetchMock = vi.mocked(globalThis.fetch)
    expect(fetchMock.mock.calls[0][1]?.method).toBe('POST')
    expect(fetchMock.mock.calls[0][0]).toContain('/ingest')
  })

  it('generateReport POSTs with period', async () => {
    await mockFetch(200, { id: 1, period: '1m', paper_count: 6 })
    await generateReport('1m')
    const fetchMock = vi.mocked(globalThis.fetch)
    expect(fetchMock.mock.calls[0][1]?.method).toBe('POST')
    expect(fetchMock.mock.calls[0][0]).toContain('/reports/generate?period=1m')
  })

  it('throws on non-ok response', async () => {
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
