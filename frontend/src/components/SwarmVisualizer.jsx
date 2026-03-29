/**
 * 3D swarm visualizer using React Three Fiber InstancedMesh.
 *
 * Architecture:
 *   WebSocket → agentBufferRef.current (no React state) → useFrame reads
 *   at 60 FPS → sets InstancedMesh matrix + color per agent → one GPU draw call.
 *
 * The 10 FPS server tick rate and 60 FPS render are decoupled via the ref
 * buffer.  matrixScratch and colorScratch are allocated once via useMemo
 * and reused every frame — zero per-frame heap allocations on the hot path.
 */
import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { Matrix4, Color } from 'three'
import { useSimulationStore } from '../store/simulationStore.js'
import { useSimulationSocket } from '../hooks/useSimulationSocket.js'

/** Maximum number of InstancedMesh instances (agent capacity). */
export const MAX_AGENTS = 1000

/** Color map: AgentStateEnum value → hex color. */
const STATE_COLORS = {
  NEUTRAL: '#4a90d9',     // blue
  EXCITED: '#e8511a',     // orange-red
  INHIBITED: '#6a4c93',   // purple
  PROPAGATING: '#f7b731', // yellow
  EXHAUSTED: '#808080',   // grey
}

/**
 * Inner mesh component — runs inside the Canvas context so useFrame works.
 * Reads from agentBufferRef every frame and updates InstancedMesh transforms.
 */
function SwarmMesh() {
  const meshRef = useRef()
  const agentBufferRef = useRef(null)
  const matrixScratch = useMemo(() => new Matrix4(), [])
  const colorScratch = useMemo(() => new Color(), [])

  const simulationId = useSimulationStore((s) => s.simulationId)
  useSimulationSocket(simulationId, agentBufferRef)

  useFrame(() => {
    const mesh = meshRef.current
    if (!mesh || !agentBufferRef.current?.agents) return

    const agents = agentBufferRef.current.agents
    const count = Math.min(agents.length, MAX_AGENTS)

    for (let i = 0; i < count; i++) {
      const a = agents[i]

      // Position
      matrixScratch.identity()
      matrixScratch.setPosition(a.x, a.y, a.z)
      mesh.setMatrixAt(i, matrixScratch)

      // Color by state
      colorScratch.set(STATE_COLORS[a.state] ?? '#ffffff')
      mesh.setColorAt(i, colorScratch)
    }

    // Hide excess instances by scaling to zero
    for (let i = count; i < MAX_AGENTS; i++) {
      matrixScratch.makeScale(0, 0, 0)
      mesh.setMatrixAt(i, matrixScratch)
    }

    mesh.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
  })

  return (
    <instancedMesh ref={meshRef} args={[null, null, MAX_AGENTS]}>
      <sphereGeometry args={[0.4, 6, 6]} />
      <meshStandardMaterial vertexColors />
    </instancedMesh>
  )
}

/**
 * Full-screen 3D canvas with orbit controls and the swarm mesh.
 */
export default function SwarmVisualizer() {
  return (
    <Canvas camera={{ position: [0, 0, 80], fov: 60 }}>
      <ambientLight intensity={0.5} />
      <pointLight position={[50, 50, 50]} intensity={1} />
      <OrbitControls enableDamping dampingFactor={0.05} />
      <SwarmMesh />
    </Canvas>
  )
}
