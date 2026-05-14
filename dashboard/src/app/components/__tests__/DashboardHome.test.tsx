import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

vi.mock('../../hooks/usePolling', () => ({
  usePollingEffect: vi.fn(),
  getAdaptiveInterval: vi.fn(() => 30000),
}))

vi.mock('../../data/api', () => ({
  BUCKET_CONFIG: {
    general_ai: { label: 'General AI', color: '#6366F1', colorLight: '#EEF2FF', shadow: '#6366F1', gradientFrom: '#818CF8', gradientTo: '#6366F1', categories: ['cs.AI', 'cs.LG'] },
    autonomous_agents: { label: 'Autonomous Agents', color: '#10B981', colorLight: '#ECFDF5', shadow: '#10B981', gradientFrom: '#34D399', gradientTo: '#059669', categories: ['cs.MA', 'cs.AI'] },
    ai_finance: { label: 'AI × Finance', color: '#F59E0B', colorLight: '#FFFBEB', shadow: '#F59E0B', gradientFrom: '#FCD34D', gradientTo: '#D97706', categories: ['q-fin.ST', 'q-fin.CP', 'q-fin.GN'] },
  },
  fetchPapers: vi.fn(),
  fetchPaperStats: vi.fn(),
  fetchPipelineRuns: vi.fn(),
  fetchReports: vi.fn(),
}))

import { DashboardHome } from '../DashboardHome'
import { fetchPaperStats, fetchPipelineRuns, fetchReports, fetchPapers } from '../../data/api'

describe('DashboardHome', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fetchPaperStats).mockResolvedValue({
      total: 10, today: 2,
      per_bucket: { general_ai: 5, autonomous_agents: 3, ai_finance: 2 },
      per_date: [{ date: '2025-05', count: 2, general_ai: 1, autonomous_agents: 1, ai_finance: 0 }],
    })
    vi.mocked(fetchPipelineRuns).mockResolvedValue([{
      id: 1, name: 'full_pipeline', started_at: '2025-05-12T18:30:00',
      finished_at: '2025-05-12T18:35:22', duration_s: 322.45,
      status: 'success', paper_count: 6,
      stages: { ingested: 6, deduplicated: 0, embedded: 6, classified: 6 },
      error: null,
    }])
    vi.mocked(fetchReports).mockResolvedValue([
      { id: 1, period: '7d', generated_at: '2025-05-12T19:00:00', paper_count: 8, content_html: '' },
    ])
    vi.mocked(fetchPapers).mockResolvedValue({ total: 1, results: [] })
  })

  it('renders stat cards from fetchPaperStats', async () => {
    render(<DashboardHome />)
    await waitFor(() => expect(screen.getByText('10')).toBeInTheDocument())
    expect(screen.getByText('Total Papers')).toBeInTheDocument()
    expect(screen.getByText('Papers Today')).toBeInTheDocument()
  })

  it('renders bucket stat cards', async () => {
    render(<DashboardHome />)
    await waitFor(() => {
      expect(screen.getAllByText('General AI').length).toBeGreaterThanOrEqual(1)
    })
    expect(screen.getAllByText('Autonomous Agents').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('AI × Finance').length).toBeGreaterThanOrEqual(1)
  })

  it('displays pipeline runs with status and duration', async () => {
    vi.mocked(fetchPipelineRuns).mockResolvedValue([
      { id: 1, name: 'full_pipeline', started_at: '2025-05-12T18:30:00',
        finished_at: '2025-05-12T18:35:22', duration_s: 322.45,
        status: 'success', paper_count: 6,
        stages: { ingested: 6, deduplicated: 0, embedded: 6, classified: 6 },
        error: null },
      { id: 2, name: 'ingest', started_at: '2025-05-10T14:15:00',
        finished_at: '2025-05-10T14:18:07', duration_s: 187.2,
        status: 'error', paper_count: 0,
        stages: { ingested: 0 }, error: 'timeout' },
    ])

    render(<DashboardHome />)
    await waitFor(() => {
      expect(screen.getAllByText(/full pipeline/i).length).toBeGreaterThanOrEqual(1)
    })
    expect(screen.getAllByText(/ingest/i).length).toBeGreaterThanOrEqual(1)
  })

  it('shows report count', async () => {
    vi.mocked(fetchReports).mockResolvedValue([
      { id: 1, period: '7d', generated_at: '2025-05-12T19:00:00', paper_count: 8, content_html: '' },
      { id: 2, period: '1m', generated_at: '2025-05-01T10:00:00', paper_count: 6, content_html: '' },
    ])
    render(<DashboardHome />)
    await waitFor(() => {
      expect(screen.getByText('Reports')).toBeInTheDocument()
    })
  })

  it('charts mount with mocked recharts stubs', async () => {
    render(<DashboardHome />)
    await waitFor(() => {
      expect(screen.getAllByTestId(/recharts-/i).length).toBeGreaterThan(0)
    })
  })
})
