/**
 * Root application layout.
 *
 * Full-screen black background with the 3D swarm filling the viewport.
 * ControlPanel and HUD are absolute-positioned overlays.
 */
import SwarmVisualizer from './components/SwarmVisualizer.jsx'
import ControlPanel from './components/ControlPanel.jsx'
import HUD from './components/HUD.jsx'

export default function App() {
  return (
    <div className="w-screen h-screen bg-black relative overflow-hidden">
      {/* 3D canvas — fills entire screen */}
      <SwarmVisualizer />

      {/* Control panel — top left */}
      <div className="absolute top-4 left-4 z-10">
        <ControlPanel />
      </div>

      {/* HUD — top right */}
      <div className="absolute top-4 right-4 z-10">
        <HUD />
      </div>
    </div>
  )
}
