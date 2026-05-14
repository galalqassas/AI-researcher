import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { usePollingEffect, getAdaptiveInterval } from '../../hooks/usePolling'

describe('usePollingEffect', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('calls callback on the given interval', async () => {
    const cb = vi.fn()
    renderHook(() => usePollingEffect(cb, 1000))
    expect(cb).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(1000)
    expect(cb).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(1000)
    expect(cb).toHaveBeenCalledTimes(2)
  })

  it('does not schedule when interval is <= 0', () => {
    const cb = vi.fn()
    renderHook(() => usePollingEffect(cb, 0))
    vi.advanceTimersByTime(5000)
    expect(cb).not.toHaveBeenCalled()
  })

  it('pauses when document is hidden', async () => {
    const cb = vi.fn()
    renderHook(() => usePollingEffect(cb, 1000))
    Object.defineProperty(document, 'hidden', { value: true, writable: true, configurable: true })
    await vi.advanceTimersByTimeAsync(3000)
    expect(cb).not.toHaveBeenCalled()
  })

  it('resumes instantly when tab becomes visible', async () => {
    const cb = vi.fn()
    renderHook(() => usePollingEffect(cb, 1000))
    Object.defineProperty(document, 'hidden', { value: true, writable: true, configurable: true })
    await vi.advanceTimersByTimeAsync(2000)
    expect(cb).not.toHaveBeenCalled()
    Object.defineProperty(document, 'hidden', { value: false, writable: true, configurable: true })
    document.dispatchEvent(new Event('visibilitychange'))
    await vi.advanceTimersByTimeAsync(0)
    expect(cb).toHaveBeenCalledTimes(1)
  })

  it('prevents overlapping executions', async () => {
    const cb = vi.fn(async () => {
      await new Promise((r) => setTimeout(r, 2500))
    })
    renderHook(() => usePollingEffect(cb, 1000))
    await vi.advanceTimersByTimeAsync(1000)
    expect(cb).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(1000)
    expect(cb).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(1500)
    expect(cb).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(1000)
    expect(cb).toHaveBeenCalledTimes(2)
  })

  it('cleans up timer on unmount', async () => {
    const cb = vi.fn()
    const { unmount } = renderHook(() => usePollingEffect(cb, 1000))
    unmount()
    await vi.advanceTimersByTimeAsync(5000)
    expect(cb).not.toHaveBeenCalled()
  })
})

describe('getAdaptiveInterval', () => {
  it('returns 30000 when runs is undefined', () => {
    expect(getAdaptiveInterval(undefined)).toBe(30000)
  })

  it('returns 3000 when any run is running', () => {
    expect(getAdaptiveInterval([{ status: 'success' }, { status: 'running' }])).toBe(3000)
  })

  it('returns 30000 when no run is running', () => {
    expect(getAdaptiveInterval([{ status: 'success' }, { status: 'error' }])).toBe(30000)
  })
})
