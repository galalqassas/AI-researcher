import { describe, it, expect } from 'vitest'
import * as Recharts from 'recharts'

describe('recharts import', () => {
  it('imports without crashing', () => {
    expect(Recharts.AreaChart).toBeDefined()
    expect(Recharts.ResponsiveContainer).toBeDefined()
  })
})
