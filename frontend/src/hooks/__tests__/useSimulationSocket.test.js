/**
 * Tests for useSimulationSocket hook.
 * Written before implementation (TDD).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, cleanup } from '@testing-library/react'

// Mock WebSocket
class MockWebSocket {
  static instances = []

  constructor(url) {
    this.url = url
    this.readyState = 0 // CONNECTING
    this.onopen = null
    this.onmessage = null
    this.onerror = null
    this.onclose = null
    this.close = vi.fn()
    MockWebSocket.instances.push(this)
    // Auto-open on next microtask
    queueMicrotask(() => {
      this.readyState = 1 // OPEN
      this.onopen?.({ type: 'open' })
    })
  }

  simulateMessage(data) {
    this.onmessage?.({ data: JSON.stringify(data) })
  }
}

// Mock Zustand store
vi.mock('../../store/simulationStore.js', () => {
  const setStatus = vi.fn()
  const incrementTick = vi.fn()
  return {
    useSimulationStore: Object.assign(
      (selector) => selector({ setStatus, incrementTick }),
      {
        getState: () => ({ setStatus, incrementTick }),
      },
    ),
    __mockSetStatus: setStatus,
    __mockIncrementTick: incrementTick,
  }
})

let useSimulationSocket

beforeEach(async () => {
  MockWebSocket.instances = []
  global.WebSocket = MockWebSocket
  vi.resetModules()
  // Re-import to get fresh module
  const mod = await import('../../hooks/useSimulationSocket.js')
  useSimulationSocket = mod.useSimulationSocket
})

afterEach(() => {
  cleanup()
  delete global.WebSocket
})

describe('useSimulationSocket', () => {
  it('does not connect when simulationId is null', () => {
    const ref = { current: null }
    renderHook(() => useSimulationSocket(null, ref))
    expect(MockWebSocket.instances).toHaveLength(0)
  })

  it('connects when simulationId is provided', async () => {
    const ref = { current: null }
    renderHook(() => useSimulationSocket('sim-1', ref))
    expect(MockWebSocket.instances).toHaveLength(1)
    expect(MockWebSocket.instances[0].url).toContain('sim-1')
  })

  it('writes parsed data to agentBufferRef', async () => {
    const ref = { current: null }
    renderHook(() => useSimulationSocket('sim-1', ref))

    const ws = MockWebSocket.instances[0]
    const payload = { tick: 1, agents: [{ id: 0, x: 1 }] }

    act(() => {
      ws.simulateMessage(payload)
    })

    expect(ref.current).toEqual(payload)
  })

  it('closes WebSocket on cleanup', () => {
    const ref = { current: null }
    const { unmount } = renderHook(() => useSimulationSocket('sim-1', ref))
    const ws = MockWebSocket.instances[0]

    unmount()
    expect(ws.close).toHaveBeenCalled()
  })
})
