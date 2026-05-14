import { vi } from 'vitest'
import type { Paper, PipelineRun, Report, PaperStats, SearchResult } from '../../app/data/api'

export const mockFetchPapers = vi.fn()
export const mockFetchPaperStats = vi.fn()
export const mockFetchPipelineRuns = vi.fn()
export const mockFetchReports = vi.fn()
export const mockFetchReport = vi.fn()
export const mockSearchPapers = vi.fn()
export const mockRunPipeline = vi.fn()
export const mockGenerateReport = vi.fn()

vi.mock('../../app/data/api', () => ({
  BUCKET_CONFIG: {
    general_ai: {
      label: 'General AI',
      color: '#6366F1',
      colorLight: '#EEF2FF',
      shadow: '#6366F1',
      gradientFrom: '#818CF8',
      gradientTo: '#6366F1',
      categories: ['cs.AI', 'cs.LG'],
    },
    autonomous_agents: {
      label: 'Autonomous Agents',
      color: '#10B981',
      colorLight: '#ECFDF5',
      shadow: '#10B981',
      gradientFrom: '#34D399',
      gradientTo: '#059669',
      categories: ['cs.MA', 'cs.AI'],
    },
    ai_finance: {
      label: 'AI × Finance',
      color: '#F59E0B',
      colorLight: '#FFFBEB',
      shadow: '#F59E0B',
      gradientFrom: '#FCD34D',
      gradientTo: '#D97706',
      categories: ['q-fin.ST', 'q-fin.CP', 'q-fin.GN'],
    },
  },
  fetchPapers: mockFetchPapers,
  fetchPaperStats: mockFetchPaperStats,
  fetchPipelineRuns: mockFetchPipelineRuns,
  fetchReports: mockFetchReports,
  fetchReport: mockFetchReport,
  searchPapers: mockSearchPapers,
  runPipeline: mockRunPipeline,
  generateReport: mockGenerateReport,
}))

// ── Factory helpers ──────────────────────────────────────────────────────────

export function makePaper(overrides: Partial<Paper> = {}): Paper {
  return {
    id: 1,
    arxiv_id: '2401.12345',
    title: 'Test Paper',
    authors: 'A. Author',
    abstract: 'An abstract.',
    published_date: '2024-01-15',
    ingested_at: '2025-05-12T18:30:00',
    buckets: ['general_ai'],
    ...overrides,
  }
}

export function makePipelineRun(overrides: Partial<PipelineRun> = {}): PipelineRun {
  return {
    id: 1,
    name: 'ingest',
    started_at: '2025-05-12T18:30:00',
    finished_at: '2025-05-12T18:35:00',
    duration_s: 300,
    status: 'success',
    paper_count: 5,
    stages: { ingested: 5, deduplicated: 0, embedded: 5, classified: 5 },
    error: null,
    ...overrides,
  }
}

export function makeReport(overrides: Partial<Report> = {}): Report {
  return {
    id: 1,
    period: '7d',
    generated_at: '2025-05-12T19:00:00',
    paper_count: 8,
    content_html: '<p>Hello</p>',
    ...overrides,
  }
}

export function makeStats(overrides: Partial<PaperStats> = {}): PaperStats {
  return {
    total: 10,
    today: 2,
    per_bucket: { general_ai: 5, autonomous_agents: 3, ai_finance: 2 },
    per_date: [
      { date: '2025-05-12', count: 2, general_ai: 1, autonomous_agents: 1, ai_finance: 0 },
    ],
    ...overrides,
  }
}

export function makeSearchResult(overrides: Partial<SearchResult> = {}): SearchResult {
  return {
    id: 1,
    arxiv_id: '2401.12345',
    title: 'Test Paper',
    abstract: 'An abstract.',
    published_date: '2024-01-15',
    buckets: ['general_ai'],
    score: 0.95,
    ...overrides,
  }
}
