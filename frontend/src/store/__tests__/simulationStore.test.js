/**
 * Tests for simulationStore (Zustand).
 * Written before implementation (TDD).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Reset Zustand state between tests
let useSimulationStore

beforeEach(async () => {
  vi.restoreAllMocks()
  // Re-import to reset module-level Zustand state
  vi.resetModules()
  const mod = await import('../../store/simulationStore.js')
  useSimulationStore = mod.useSimulationStore
})

describe('simulationStore', () => {
  it('has correct initial state', () => {
    const state = useSimulationStore.getState()
    expect(state.simulationId).toBeNull()
    expect(state.connectionStatus).toBe('disconnected')
    expect(state.tickCount).toBe(0)
    expect(state.neuralSignature).toBeNull()
  })

  it('setStatus updates connectionStatus', () => {
    useSimulationStore.getState().setStatus('connected')
    expect(useSimulationStore.getState().connectionStatus).toBe('connected')
  })

  it('incrementTick increases tickCount by 1', () => {
    useSimulationStore.getState().incrementTick()
    expect(useSimulationStore.getState().tickCount).toBe(1)
    useSimulationStore.getState().incrementTick()
    expect(useSimulationStore.getState().tickCount).toBe(2)
  })

  it('startSimulation calls fetch with correct body', async () => {
    const mockResponse = {
      ok: true,
      json: () =>
        Promise.resolve({
          simulation_id: 'abc-123',
          swarm_size: 100,
          neural_signature: { ventral_striatum_reward: 0.5 },
        }),
    }
    global.fetch = vi.fn().mockResolvedValue(mockResponse)

    await useSimulationStore.getState().startSimulation('https://example.com/video', 100)

    expect(global.fetch).toHaveBeenCalledWith('/api/v1/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ media_url: 'https://example.com/video', swarm_size: 100 }),
    })
  })

  it('startSimulation sets simulationId and neuralSignature', async () => {
    const sig = { ventral_striatum_reward: 0.9 }
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          simulation_id: 'xyz-789',
          swarm_size: 200,
          neural_signature: sig,
        }),
    })

    await useSimulationStore.getState().startSimulation('https://example.com', 200)
    const state = useSimulationStore.getState()
    expect(state.simulationId).toBe('xyz-789')
    expect(state.neuralSignature).toEqual(sig)
  })

  it('startSimulation sets status to error on fetch failure', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 500 })

    await useSimulationStore.getState().startSimulation('https://example.com', 100)
    expect(useSimulationStore.getState().connectionStatus).toBe('error')
  })
})
