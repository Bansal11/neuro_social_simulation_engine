/**
 * Tests for ControlPanel component.
 * Written before implementation (TDD).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock the store
const mockStartSimulation = vi.fn()
vi.mock('../../store/simulationStore.js', () => ({
  useSimulationStore: (selector) =>
    selector({
      connectionStatus: 'disconnected',
      startSimulation: mockStartSimulation,
    }),
}))

let ControlPanel

beforeEach(async () => {
  vi.clearAllMocks()
  const mod = await import('../../components/ControlPanel.jsx')
  ControlPanel = mod.default
})

describe('ControlPanel', () => {
  it('renders media URL input', () => {
    render(<ControlPanel />)
    expect(screen.getByPlaceholderText(/url/i)).toBeInTheDocument()
  })

  it('renders swarm size slider', () => {
    render(<ControlPanel />)
    expect(screen.getByRole('slider')).toBeInTheDocument()
  })

  it('renders launch button', () => {
    render(<ControlPanel />)
    expect(screen.getByRole('button', { name: /launch/i })).toBeInTheDocument()
  })

  it('calls startSimulation on submit', async () => {
    const user = userEvent.setup()
    render(<ControlPanel />)

    const input = screen.getByPlaceholderText(/url/i)
    await user.clear(input)
    await user.type(input, 'https://example.com/video')

    const button = screen.getByRole('button', { name: /launch/i })
    await user.click(button)

    expect(mockStartSimulation).toHaveBeenCalledWith('https://example.com/video', expect.any(Number))
  })

  it('displays connection status', () => {
    render(<ControlPanel />)
    expect(screen.getByText(/disconnected/i)).toBeInTheDocument()
  })
})
