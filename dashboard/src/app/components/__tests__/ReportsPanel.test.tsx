import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('../../hooks/usePolling', () => ({
  usePollingEffect: vi.fn(),
}))

vi.mock('../../data/api', () => ({
  fetchReports: vi.fn(),
  fetchReport: vi.fn(),
  generateReport: vi.fn(),
}))

vi.mock('marked', () => ({
  marked: { setOptions: vi.fn(), parse: vi.fn((t: string) => `<p>${t}</p>`) },
  default: { setOptions: vi.fn(), parse: vi.fn((t: string) => `<p>${t}</p>`) },
}))

import { ReportsPanel } from '../ReportsPanel'
import { fetchReports, fetchReport, generateReport } from '../../data/api'

describe('ReportsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fetchReports).mockResolvedValue([
      { id: 1, period: '7d', generated_at: '2025-05-12T19:00:00', paper_count: 8, content_html: '' },
      { id: 2, period: '1m', generated_at: '2025-05-01T10:00:00', paper_count: 6, content_html: '' },
    ] as any)
    vi.mocked(generateReport).mockResolvedValue({ id: 3, period: '7d', paper_count: 5 } as any)
    vi.mocked(fetchReport).mockResolvedValue({ id: 1, period: '7d', generated_at: '2025-05-12T19:00:00', paper_count: 8, content_html: '<h1>Test Report</h1>' } as any)
  })

  it('renders period selector cards', () => {
    render(<ReportsPanel />)
    expect(screen.getByText('Last 7 Days')).toBeInTheDocument()
    expect(screen.getByText('Last Month')).toBeInTheDocument()
  })

  it('history list renders reports from fetchReports', async () => {
    render(<ReportsPanel />)
    await waitFor(() => {
      expect(screen.getByText('Last 7 Days Report')).toBeInTheDocument()
    })
    expect(screen.getByText('Last Month Report')).toBeInTheDocument()
  })

  it('clicking a report opens modal with fetched content', async () => {
    render(<ReportsPanel />)
    const user = userEvent.setup()

    await waitFor(() => screen.getByText('Last 7 Days Report'))
    await user.click(screen.getByText('Last 7 Days Report'))

    await waitFor(() => {
      expect(vi.mocked(fetchReport)).toHaveBeenCalledWith(1)
    })
    expect(screen.getByText('Test Report')).toBeInTheDocument()
  })

  it('HTML export creates a Blob and anchor click', async () => {
    const createElementSpy = vi.spyOn(document, 'createElement')

    render(<ReportsPanel />)
    const user = userEvent.setup()

    await waitFor(() => screen.getByText('Last 7 Days Report'))
    await user.click(screen.getByText('Last 7 Days Report'))

    await waitFor(() => screen.getByText('Test Report'))

    const exportBtn = screen.getByRole('button', { name: /export/i })
    await user.click(exportBtn)

    expect(createElementSpy).toHaveBeenCalledWith('a')

    createElementSpy.mockRestore()
  })
})
