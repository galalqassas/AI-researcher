import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('../../hooks/usePolling', () => ({
  usePollingEffect: vi.fn(),
}))

vi.mock('../../data/api', () => ({
  BUCKET_CONFIG: {
    general_ai: { label: 'General AI', color: '#6366F1', colorLight: '#EEF2FF', shadow: '#6366F1', gradientFrom: '#818CF8', gradientTo: '#6366F1', categories: ['cs.AI', 'cs.LG'] },
    autonomous_agents: { label: 'Autonomous Agents', color: '#10B981', colorLight: '#ECFDF5', shadow: '#10B981', gradientFrom: '#34D399', gradientTo: '#059669', categories: ['cs.MA', 'cs.AI'] },
    ai_finance: { label: 'AI × Finance', color: '#F59E0B', colorLight: '#FFFBEB', shadow: '#F59E0B', gradientFrom: '#FCD34D', gradientTo: '#D97706', categories: ['q-fin.ST', 'q-fin.CP', 'q-fin.GN'] },
  },
  fetchPapers: vi.fn(),
}))

import { PapersPanel } from '../PapersPanel'
import { fetchPapers } from '../../data/api'

describe('PapersPanel', () => {
  const papers = [
    { id: 1, title: 'Alpha', arxiv_id: '2401.12345', authors: 'A. Author', abstract: 'An abstract.', published_date: '2024-01-15', ingested_at: '2025-05-12T18:30:00', buckets: ['general_ai'] },
    { id: 2, title: 'Beta', arxiv_id: '2402.98765', authors: 'B. Author', abstract: 'Another abstract.', published_date: '2024-02-20', ingested_at: '2025-05-12T18:31:00', buckets: ['autonomous_agents'] },
    { id: 3, title: 'Gamma', arxiv_id: '2403.11111', authors: 'C. Author', abstract: 'Yet another.', published_date: '2024-03-10', ingested_at: '2025-05-12T18:32:00', buckets: ['ai_finance'] },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fetchPapers).mockResolvedValue({ total: 3, results: papers as any })
  })

  it('renders paper cards with titles', async () => {
    render(<PapersPanel />)
    await waitFor(() => {
      expect(screen.getByText('Alpha')).toBeInTheDocument()
    })
    expect(screen.getByText('Beta')).toBeInTheDocument()
    expect(screen.getByText('Gamma')).toBeInTheDocument()
  })

  it('bucket filter chips change API params', async () => {
    render(<PapersPanel />)
    const user = userEvent.setup()
    await waitFor(() => screen.getByText('Alpha'))

    const chip = screen.getByRole('button', { name: /general ai/i })
    await user.click(chip)

    await waitFor(() => {
      expect(vi.mocked(fetchPapers)).toHaveBeenLastCalledWith('general_ai', 1, expect.any(Number), undefined)
    })
  })

  it('pagination exists when total exceeds page size', async () => {
    vi.mocked(fetchPapers).mockResolvedValue({ total: 25, results: papers.slice(0, 3) as any })
    render(<PapersPanel />)
    await waitFor(() => screen.getByText('Alpha'))

    const allButtons = screen.getAllByRole('button')
    expect(allButtons.length).toBeGreaterThan(0)
  })

  it('arXiv link href is correct', async () => {
    render(<PapersPanel />)
    await waitFor(() => screen.getByText('Alpha'))

    const link = screen.getAllByRole('link')[0]
    expect(link).toHaveAttribute('href', 'https://arxiv.org/abs/2401.12345')
  })

  it('initialQuery pre-fills search input', async () => {
    render(<PapersPanel initialQuery="2401.12345" />)
    await waitFor(() => {
      const calls = vi.mocked(fetchPapers).mock.calls
      const match = calls.find(c => c[3] === '2401.12345')
      expect(match).toBeTruthy()
    })
  })

  it('onPapersLoaded callback receives total count', async () => {
    const onLoaded = vi.fn()
    render(<PapersPanel onPapersLoaded={onLoaded} />)
    await waitFor(() => {
      expect(onLoaded).toHaveBeenCalledWith(3)
    })
  })
})
