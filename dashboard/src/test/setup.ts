import { createElement } from 'react'
import { expect, afterEach, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'

// Mock heavy external libraries that break or are slow in jsdom
vi.mock('recharts', () => {
  const components = [
    'AreaChart', 'Area', 'XAxis', 'YAxis', 'CartesianGrid', 'Tooltip',
    'ResponsiveContainer', 'PieChart', 'Pie', 'Cell', 'BarChart', 'Bar',
    'Legend', 'LineChart', 'Line',
  ]
  const mocked: Record<string, any> = {}
  components.forEach((name) => {
    mocked[name] = (props: any) => createElement('div', { 'data-testid': `recharts-${name}`, ...props })
  })
  return mocked
})

vi.mock('marked', () => ({
  marked: { setOptions: vi.fn(), parse: vi.fn((t: string) => `<p>${t}</p>`) },
  default: { setOptions: vi.fn(), parse: vi.fn((t: string) => `<p>${t}</p>`) },
}))

// matchMedia for Radix/shadcn
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})
