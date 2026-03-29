/**
 * Tests for HUD component.
 * Written before implementation (TDD).
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

const MOCK_SIGNATURE = {
  ventral_striatum_reward: 0.8,
  anterior_insula_valence: 0.4,
  amygdala_arousal: 0.6,
  prefrontal_cortex_regulation: 0.3,
  nucleus_accumbens_motivation: 0.9,
  posterior_superior_temporal_sulcus_social: 0.5,
}

let mockState = {}

vi.mock('../../store/simulationStore.js', () => ({
  useSimulationStore: (selector) => selector(mockState),
}))

let HUD

beforeEach(async () => {
  const mod = await import('../../components/HUD.jsx')
  HUD = mod.default
})

describe('HUD', () => {
  it('renders tick count', () => {
    mockState = { tickCount: 42, connectionStatus: 'connected', neuralSignature: null }
    render(<HUD />)
    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('renders connection status', () => {
    mockState = { tickCount: 0, connectionStatus: 'connected', neuralSignature: null }
    render(<HUD />)
    expect(screen.getByText(/connected/i)).toBeInTheDocument()
  })

  it('renders neural signature bars when signature is present', () => {
    mockState = { tickCount: 10, connectionStatus: 'connected', neuralSignature: MOCK_SIGNATURE }
    render(<HUD />)
    // Should render one bar per fMRI region
    const bars = screen.getAllByTestId('sig-bar')
    expect(bars).toHaveLength(6)
  })

  it('does not render bars when signature is null', () => {
    mockState = { tickCount: 0, connectionStatus: 'disconnected', neuralSignature: null }
    render(<HUD />)
    expect(screen.queryAllByTestId('sig-bar')).toHaveLength(0)
  })
})
