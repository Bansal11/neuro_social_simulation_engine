/**
 * Tests for SwarmVisualizer component.
 * Written before implementation (TDD).
 *
 * Three.js Canvas is mocked in setupTests.js — these are structural tests,
 * not visual integration tests. The useFrame + InstancedMesh path is tested
 * by contract (the hook test covers the buffer write side; full visual
 * testing is manual).
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

// Mock the store
vi.mock('../../store/simulationStore.js', () => ({
  useSimulationStore: (selector) =>
    selector({ simulationId: null }),
}))

// Mock the socket hook (no real WS in tests)
vi.mock('../../hooks/useSimulationSocket.js', () => ({
  useSimulationSocket: vi.fn(),
}))

let SwarmVisualizer

beforeEach(async () => {
  const mod = await import('../../components/SwarmVisualizer.jsx')
  SwarmVisualizer = mod.default
})

describe('SwarmVisualizer', () => {
  it('renders the R3F canvas container', () => {
    render(<SwarmVisualizer />)
    // Our setupTests.js mocks Canvas as a div with data-testid="r3f-canvas"
    expect(screen.getByTestId('r3f-canvas')).toBeInTheDocument()
  })

  it('exports MAX_AGENTS constant equal to 1000', async () => {
    const mod = await import('../../components/SwarmVisualizer.jsx')
    expect(mod.MAX_AGENTS).toBe(1000)
  })
})
