import { describe, it, expect } from 'vitest'

describe('debug', () => {
  it('can import DashboardHome module', async () => {
    const mod = await import('../DashboardHome')
    expect(mod.DashboardHome).toBeDefined()
  })
})
