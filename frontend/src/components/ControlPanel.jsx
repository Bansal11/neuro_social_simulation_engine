/**
 * Control panel overlay for launching simulations.
 *
 * Uses local React state for form inputs (non-performance-critical).
 * On submit, calls startSimulation from the Zustand store which POSTs
 * to the backend and triggers the WebSocket connection flow.
 */
import { useState } from 'react'
import { useSimulationStore } from '../store/simulationStore.js'

const STATUS_COLORS = {
  disconnected: 'bg-gray-500',
  connecting: 'bg-yellow-500',
  connected: 'bg-green-500',
  error: 'bg-red-500',
}

export default function ControlPanel() {
  const [mediaUrl, setMediaUrl] = useState('')
  const [swarmSize, setSwarmSize] = useState(500)

  const connectionStatus = useSimulationStore((s) => s.connectionStatus)
  const startSimulation = useSimulationStore((s) => s.startSimulation)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!mediaUrl.trim()) return
    startSimulation(mediaUrl.trim(), swarmSize)
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-black/70 backdrop-blur-sm rounded-lg p-4 text-white w-80 space-y-4"
    >
      <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-300">
        Simulation Control
      </h2>

      {/* Media URL */}
      <input
        type="text"
        value={mediaUrl}
        onChange={(e) => setMediaUrl(e.target.value)}
        placeholder="Media URL (video, audio, image)"
        className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
      />

      {/* Swarm size slider */}
      <div>
        <label className="text-xs text-gray-400 flex justify-between">
          <span>Swarm Size</span>
          <span>{swarmSize}</span>
        </label>
        <input
          type="range"
          min={100}
          max={5000}
          step={100}
          value={swarmSize}
          onChange={(e) => setSwarmSize(Number(e.target.value))}
          className="w-full"
        />
      </div>

      {/* Launch button */}
      <button
        type="submit"
        className="w-full bg-blue-600 hover:bg-blue-500 transition rounded py-2 text-sm font-medium"
      >
        Launch Simulation
      </button>

      {/* Connection status badge */}
      <div className="flex items-center gap-2 text-xs text-gray-400">
        <span className={`inline-block w-2 h-2 rounded-full ${STATUS_COLORS[connectionStatus]}`} />
        <span>{connectionStatus}</span>
      </div>
    </form>
  )
}
