import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('../../hooks/usePolling', () => ({
  usePollingEffect: vi.fn(),
  getAdaptiveInterval: vi.fn(() => 30000),
}))

vi.mock('../../data/api', () => ({
  searchPapers: vi.fn(),
  fetchPipelineRuns: vi.fn(),
  fetchPaperStats: vi.fn(),
}))

vi.mock('../../components/DashboardHome', () => ({
  DashboardHome: () => <div data-testid="dashboard-home">DashboardHome</div>,
}))

vi.mock('../../components/ReportsPanel', () => ({
  ReportsPanel: () => <div data-testid="reports-panel">ReportsPanel</div>,
}))

vi.mock('../../components/PapersPanel', () => ({
  PapersPanel: (props: any) => (
    <div data-testid="papers-panel">
      PapersPanel {props.initialQuery ? `query=${props.initialQuery}` : ''}
    </div>
  ),
}))

vi.mock('../../components/PipelinePanel', () => ({
  PipelinePanel: () => <div data-testid="pipeline-panel">PipelinePanel</div>,
}))

import App from '../../App'
import { fetchPipelineRuns, fetchPaperStats, searchPapers } from '../../data/api'

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fetchPipelineRuns).mockResolvedValue([{
      id: 1, name: 'ingest', started_at: '2025-05-12T18:30:00',
      finished_at: '2025-05-12T18:35:00', duration_s: 300,
      status: 'success', paper_count: 5,
      stages: { ingested: 5, deduplicated: 0, embedded: 5, classified: 5 },
      error: null,
    }] as any)
    vi.mocked(fetchPaperStats).mockResolvedValue({
      total: 42, today: 2,
      per_bucket: { general_ai: 20, autonomous_agents: 12, ai_finance: 10 },
      per_date: [{ date: '2025-05-12', count: 2, general_ai: 1, autonomous_agents: 1, ai_finance: 0 }],
    } as any)
    vi.mocked(searchPapers).mockResolvedValue({ query: '', results: [] } as any)
  })

  it('renders sidebar nav and defaults to dashboard', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText('Auto-Researcher', { selector: 'p' })).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /^Dashboard$/i })).toBeInTheDocument()
    expect(screen.getByTestId('dashboard-home')).toBeInTheDocument()
  })

  it('sidebar navigation switches pages', async () => {
    render(<App />)
    const user = userEvent.setup()

    await waitFor(() => screen.getByRole('button', { name: /^Dashboard$/i }))

    const reportsBtn = screen.getByRole('button', { name: /reports/i })
    await user.click(reportsBtn)
    expect(screen.getByTestId('reports-panel')).toBeInTheDocument()

    const pipelineBtn = screen.getByRole('button', { name: /pipeline/i })
    await user.click(pipelineBtn)
    expect(screen.getByTestId('pipeline-panel')).toBeInTheDocument()
  })

  it('opens search modal via header button', async () => {
    render(<App />)
    const user = userEvent.setup()
    await waitFor(() => screen.getByRole('button', { name: /^Dashboard$/i }))

    const searchBtn = screen.getAllByRole('button', { name: /search/i })[1]
    await user.click(searchBtn)
    expect(screen.getByPlaceholderText(/search papers/i)).toBeInTheDocument()
  })
})
