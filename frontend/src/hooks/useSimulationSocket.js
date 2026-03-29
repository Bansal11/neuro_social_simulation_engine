/**
 * Custom hook: connects a WebSocket to the simulation engine and writes
 * incoming tick data directly to agentBufferRef — zero React state updates
 * on the hot path.
 *
 * @param {string | null} simulationId - UUID from the Zustand store (null = do nothing).
 * @param {React.MutableRefObject} agentBufferRef - Ref whose .current is overwritten
 *   with the parsed SimulationTick JSON on every WebSocket message.
 */
import { useEffect } from 'react'
import { useSimulationStore } from '../store/simulationStore.js'

export function useSimulationSocket(simulationId, agentBufferRef) {
  const setStatus = useSimulationStore((s) => s.setStatus)
  const incrementTick = useSimulationStore((s) => s.incrementTick)

  useEffect(() => {
    if (!simulationId) return

    // Build WS URL relative to the current host (works behind Vite proxy and in production)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/${simulationId}`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      setStatus('connected')
    }

    ws.onmessage = (event) => {
      // Hot path: write parsed data to ref — no setState, no re-render.
      agentBufferRef.current = JSON.parse(event.data)
      incrementTick()
    }

    ws.onerror = () => {
      setStatus('error')
    }

    ws.onclose = () => {
      setStatus('disconnected')
    }

    return () => {
      ws.close()
    }
  }, [simulationId]) // eslint-disable-line react-hooks/exhaustive-deps
}
