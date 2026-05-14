import { describe, it, expect, vi, beforeEach, type MockInstance } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('../../hooks/usePolling', () => ({
  usePollingEffect: vi.fn(),
  getAdaptiveInterval: vi.fn(() => 30000),
}))

vi.mock('../../data/api', () => ({
  fetchPipelineRuns: vi.fn(),
  runPipeline: vi.fn(),
}))

import { PipelinePanel } from '../PipelinePanel'
import { fetchPipelineRuns, runPipeline } from '../../data/api'

describe('PipelinePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fetchPipelineRuns).mockResolvedValue([
      { id: 1, name: 'full_pipeline', started_at: '2025-05-12T18:30:00',
        finished_at: '2025-05-12T18:35:00', duration_s: 300, status: 'success',
        paper_count: 5, stages: { ingested: 5, deduplicated: 0, embedded: 5, classified: 5 }, error: null },
      { id: 2, name: 'ingest', started_at: '2025-05-10T14:15:00',
        finished_at: '2025-05-10T14:18:00', duration_s: 45, status: 'error',
        paper_count: 0, stages: { ingested: 0 }, error: 'timeout' },
      { id: 3, name: 'report', started_at: '2025-05-08T09:00:00',
        finished_at: '2025-05-08T09:02:00', duration_s: 150, status: 'success',
        paper_count: 3, stages: null, error: null },
    ] as any)
    vi.mocked(runPipeline).mockResolvedValue({ status: 'ok', paper_count: 2, stages: { ingested: 2 } } as any)
  })

  it('computes and displays success rate stat', async () => {
    render(<PipelinePanel />)
    await waitFor(() => {
      expect(screen.getAllByText(/67%/).length).toBeGreaterThanOrEqual(1)
    })
  })

  it('computes average duration', async () => {
    render(<PipelinePanel />)
    await waitFor(() => {
      expect(screen.getByText('2.5m')).toBeInTheDocument()
    })
  })

  it('displays total papers processed', async () => {
    render(<PipelinePanel />)
    await waitFor(() => {
      // total papers = sum of paper_count for ingest/full_pipeline success runs
      // run 1 (full_pipeline, success) has 5, run 3 (report, success) is excluded
      expect(screen.getAllByText('5').length).toBeGreaterThanOrEqual(1)
    })
  })

  it('bar chart mounts with mocked recharts stubs', async () => {
    render(<PipelinePanel />)
    await waitFor(() => {
      expect(screen.getAllByTestId(/recharts-/i).length).toBeGreaterThan(0)
    })
  })

  it('Run Pipeline button calls runPipeline()', async () => {
    render(<PipelinePanel />)
    const user = userEvent.setup()

    const btn = screen.getByRole('button', { name: /run pipeline/i })
    await user.click(btn)

    await waitFor(() => {
      expect(vi.mocked(runPipeline)).toHaveBeenCalledTimes(1)
    })
  })

  it('expandable run shows stage breakdown', async () => {
    vi.mocked(fetchPipelineRuns).mockResolvedValue([
      { id: 1, name: 'ingest', started_at: '2025-05-12T18:30:00',
        finished_at: '2025-05-12T18:35:00', duration_s: 300, status: 'success',
        paper_count: 5, stages: { ingested: 5, deduplicated: 1, embedded: 5, classified: 5 }, error: null },
    ] as any)

    render(<PipelinePanel />)
    const user = userEvent.setup()
    // Use exact match to get the run-name text (not "ingested across all runs" stat card)
    await waitFor(() => screen.getByText('ingest'))
    const runRow = screen.getByText('ingest').closest('button')
    if (runRow) await user.click(runRow)

    await waitFor(() => {
      // Stage Breakdown heading is rendered once an expandable run is opened
      expect(screen.getByText('Stage Breakdown')).toBeInTheDocument()
    })
    expect(screen.getAllByText('5').length).toBeGreaterThanOrEqual(1)
  })

  it('shows error message for failed runs', async () => {
    vi.mocked(fetchPipelineRuns).mockResolvedValue([
      { id: 1, name: 'ingest', started_at: '2025-05-12T18:30:00',
        finished_at: '2025-05-12T18:30:45', duration_s: 45, status: 'error',
        paper_count: 0, stages: { ingested: 0 }, error: 'Ollama connection timeout' },
    ] as any)

    render(<PipelinePanel />)
    // Use exact match to get the run-name text (not "ingested across all runs" stat card)
    await waitFor(() => screen.getByText('ingest'))
    const runRow = screen.getByText('ingest').closest('button')
    const user = userEvent.setup()
    if (runRow) await user.click(runRow)

    await waitFor(() => {
      expect(screen.getByText(/Ollama connection timeout/)).toBeInTheDocument()
    })
  })
})
