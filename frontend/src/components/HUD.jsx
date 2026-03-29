/**
 * Heads-up display overlay showing tick count, connection status,
 * and neural signature bar chart.
 *
 * Reads from Zustand store — does not interact with the 3D render path.
 */
import { useSimulationStore } from '../store/simulationStore.js'

/** Short display labels for the six fMRI regions. */
const REGION_LABELS = {
  ventral_striatum_reward: 'Reward',
  anterior_insula_valence: 'Valence',
  amygdala_arousal: 'Arousal',
  prefrontal_cortex_regulation: 'Regulation',
  nucleus_accumbens_motivation: 'Motivation',
  posterior_superior_temporal_sulcus_social: 'Social',
}

export default function HUD() {
  const tickCount = useSimulationStore((s) => s.tickCount)
  const connectionStatus = useSimulationStore((s) => s.connectionStatus)
  const neuralSignature = useSimulationStore((s) => s.neuralSignature)

  return (
    <div className="bg-black/70 backdrop-blur-sm rounded-lg p-4 text-white w-64 space-y-3">
      {/* Tick counter */}
      <div className="flex justify-between text-xs text-gray-400">
        <span>Tick</span>
        <span>{tickCount}</span>
      </div>

      {/* Status */}
      <div className="flex justify-between text-xs text-gray-400">
        <span>Status</span>
        <span className={connectionStatus === 'connected' ? 'text-green-400' : 'text-gray-500'}>
          {connectionStatus}
        </span>
      </div>

      {/* Neural signature bars */}
      {neuralSignature && (
        <div className="space-y-1">
          <div className="text-xs text-gray-400 font-semibold uppercase tracking-wider">
            Neural Signature
          </div>
          {Object.entries(neuralSignature).map(([key, value]) => (
            <div key={key} data-testid="sig-bar" className="flex items-center gap-2">
              <span className="text-[10px] text-gray-500 w-16 truncate">
                {REGION_LABELS[key] ?? key}
              </span>
              <div className="flex-1 h-2 bg-gray-800 rounded overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded"
                  style={{ width: `${(value * 100).toFixed(0)}%` }}
                />
              </div>
              <span className="text-[10px] text-gray-500 w-6 text-right">
                {value.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
