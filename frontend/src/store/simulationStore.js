/**
 * Zustand store for simulation UI state.
 *
 * This store holds non-render-critical state: simulation metadata, connection
 * status, and the tick counter.  Per-tick agent positions are NOT stored here —
 * they flow through a useRef buffer directly to the InstancedMesh in useFrame.
 */
import { create } from 'zustand'

export const useSimulationStore = create((set) => ({
  // --- State ---
  simulationId: null,
  connectionStatus: 'disconnected', // 'disconnected' | 'connecting' | 'connected' | 'error'
  swarmSize: 500,
  mediaUrl: '',
  neuralSignature: null,
  tickCount: 0,

  // --- Actions ---

  /**
   * POST to /api/v1/simulate and set simulationId + neuralSignature on success.
   * @param {string} mediaUrl
   * @param {number} swarmSize
   */
  startSimulation: async (mediaUrl, swarmSize) => {
    set({ connectionStatus: 'connecting', tickCount: 0 })
    try {
      const res = await fetch('/api/v1/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ media_url: mediaUrl, swarm_size: swarmSize }),
      })
      if (!res.ok) {
        set({ connectionStatus: 'error' })
        return
      }
      const data = await res.json()
      set({
        simulationId: data.simulation_id,
        swarmSize: data.swarm_size,
        neuralSignature: data.neural_signature,
        mediaUrl,
      })
    } catch {
      set({ connectionStatus: 'error' })
    }
  },

  /** @param {'disconnected' | 'connecting' | 'connected' | 'error'} status */
  setStatus: (status) => set({ connectionStatus: status }),

  incrementTick: () => set((s) => ({ tickCount: s.tickCount + 1 })),
}))
