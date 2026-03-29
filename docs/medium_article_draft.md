# I Built an Engine That Gives AI Agents a Nervous System — Here's the Architecture

*How I bridged computational neuroscience with social swarm simulation using FastAPI, WebSockets, and React Three Fiber*

---

What if you could predict whether a piece of content would go viral — not by analysing engagement metrics after the fact, but by simulating how it would biologically resonate with people *before* anyone sees it?

That's the premise behind the **Neuro-Social Simulation Engine**, a system I've been building that does something I haven't seen attempted before: it extracts a "neural signature" from media (predicted brain activations), injects that signature into a swarm of AI agents as a biological prior, and then watches how the cascade unfolds in real time.

The result is a 3D visualization of 1,000+ agents forming clusters, propagating excitation, and self-organizing — all driven by simulated neuroscience.

In this article, I'll walk through the architecture decisions, the performance tricks that make it work at 60 FPS, and the patterns I think are broadly useful beyond this specific project.

---

## The Core Idea: Biology → Behaviour → Virality

The system has three stages:

1. **Neural Signature Extraction** — Media goes in, predicted fMRI activations come out. Six brain regions are scored: reward (ventral striatum), valence (anterior insula), arousal (amygdala), regulation (prefrontal cortex), motivation (nucleus accumbens), and social cognition (pSTS).

2. **Swarm Simulation** — Those six scores become the "biological DNA" of a multi-agent swarm. Each score directly weights a different aspect of agent behaviour — how tightly they cluster, how fast excitation spreads, when inhibition kicks in.

3. **Real-Time Visualization** — Agent states stream over WebSocket at 10 FPS. A React Three Fiber client renders them at 60 FPS with a single GPU draw call.

The key insight: the neural signature doesn't just *label* the content. It *parameterises* the entire social dynamics simulation. Different content produces genuinely different emergent behaviour.

---

## Architecture: Decoupled by Design

```
POST /api/v1/simulate → Neural Signature → Init Swarm → Background Engine
                                                              ↓ 10 FPS
WS /ws/{sim_id} ← ConnectionManager.broadcast ← SimulationTick
                                                              ↓
Browser: agentBufferRef.current = JSON.parse(data)   [no re-render]
                                                              ↓ 60 FPS
useFrame → Matrix4.setPosition → InstancedMesh → 1 GPU draw call
```

The backend is a FastAPI microservice. The frontend is React Three Fiber. They communicate via REST (to start simulations) and WebSocket (to stream real-time agent states). That's it. No shared state, no coupling — the engine can run headless, feed a different frontend, or be consumed by another service.

---

## Modelling Biological States as a State Machine

Every agent in the swarm has a biological state inspired by neural activation dynamics:

```python
class AgentStateEnum(str, enum.Enum):
    NEUTRAL     = "NEUTRAL"      # baseline resting state
    EXCITED     = "EXCITED"      # high reward-driven activity
    INHIBITED   = "INHIBITED"    # prefrontal down-regulation
    PROPAGATING = "PROPAGATING"  # spreading activation to neighbours
    EXHAUSTED   = "EXHAUSTED"    # post-excitation refractory period
```

This isn't just labelling. The state machine has real transition rules:

- An agent becomes **EXCITED** when its neighbours push its influence score past a threshold
- **PROPAGATING** kicks in when an excited agent has motivated neighbours — this is the viral cascade mechanism
- **INHIBITED** fires when the regulation signal is high — the prefrontal cortex "puts the brakes on"
- **EXHAUSTED** is a refractory period after sustained excitation — you can't stay hyped forever, and neither can the agents

The transitions are biologically inspired. Real neurons have refractory periods. Real social cascades have saturation points. Encoding this into the state machine gives the simulation behaviour that *feels* right even before we plug in real neuroscience models.

---

## The 10/60 FPS Decoupling Problem

Here's the core performance challenge: the simulation engine runs at 10 FPS (each tick involves non-trivial computation for 1,000 agents). But the 3D visualization needs to render at 60 FPS or the user experience is terrible.

The standard React approach — `useState` to store WebSocket data — would be catastrophic. Every incoming message would trigger a re-render, and React's reconciler would choke on 1,000-agent state arrays 10 times per second.

The solution: **never put the agent data in React state at all.**

```javascript
export function useSimulationSocket(simulationId, agentBufferRef) {
  const setStatus = useSimulationStore((s) => s.setStatus)
  const incrementTick = useSimulationStore((s) => s.incrementTick)

  useEffect(() => {
    if (!simulationId) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/${simulationId}`
    const ws = new WebSocket(wsUrl)

    ws.onmessage = (event) => {
      // Hot path: write parsed data to ref — no setState, no re-render.
      agentBufferRef.current = JSON.parse(event.data)
      incrementTick()
    }

    ws.onclose = () => setStatus('disconnected')
    return () => ws.close()
  }, [simulationId])
}
```

The WebSocket handler writes directly to a `useRef`. No `useState`. No re-render. The only React state update is `incrementTick()` — a single integer for the HUD display, which is cheap.

The render side reads from that same ref inside `useFrame`, which runs every animation frame (60 FPS) completely outside React's reconciliation cycle:

```javascript
function SwarmMesh() {
  const meshRef = useRef()
  const agentBufferRef = useRef(null)
  const matrixScratch = useMemo(() => new Matrix4(), [])
  const colorScratch = useMemo(() => new Color(), [])

  useSimulationSocket(simulationId, agentBufferRef)

  useFrame(() => {
    const mesh = meshRef.current
    if (!mesh || !agentBufferRef.current?.agents) return

    const agents = agentBufferRef.current.agents
    const count = Math.min(agents.length, MAX_AGENTS)

    for (let i = 0; i < count; i++) {
      const a = agents[i]
      matrixScratch.identity()
      matrixScratch.setPosition(a.x, a.y, a.z)
      mesh.setMatrixAt(i, matrixScratch)

      colorScratch.set(STATE_COLORS[a.state] ?? '#ffffff')
      mesh.setColorAt(i, colorScratch)
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
```

Three critical performance details here:

1. **`matrixScratch` and `colorScratch` are allocated once** via `useMemo` and reused every frame. In a 60 FPS loop, per-frame allocations are the enemy of smooth performance.

2. **InstancedMesh** renders all 1,000 agents in a single GPU draw call. Without it, you'd have 1,000 separate draw calls — a GPU bottleneck.

3. **The same server tick data renders ~6 times** before new data arrives (10 FPS ÷ 60 FPS). This is correct behaviour. If you later want smooth interpolation between ticks, you add a lerp using `useFrame`'s `delta` parameter.

---

## Self-Healing WebSocket Infrastructure

The backend needs to handle real-world WebSocket messiness: clients disconnect unexpectedly, simulations outlive their viewers, stale connections accumulate.

The `ConnectionManager` handles this with a lock-guarded connection table:

```python
async def broadcast(self, simulation_id: str, message: str) -> None:
    async with self._lock:
        sockets = set(self._connections.get(simulation_id, set()))

    stale: list[WebSocket] = []
    for ws in sockets:
        try:
            await ws.send_text(message)
        except Exception:
            stale.append(ws)

    if stale:
        async with self._lock:
            active = self._connections.get(simulation_id, set())
            for ws in stale:
                active.discard(ws)
```

Key pattern: copy the socket set under lock, iterate and send *outside* the lock (so broadcasting doesn't block new connections), then re-acquire the lock to remove stale sockets. This avoids both deadlocks and mutation-during-iteration bugs.

The simulation engine itself has a self-termination mechanism:

```python
while self.running:
    t0 = asyncio.get_event_loop().time()

    self.agents = mock_advance_swarm(self.agents, self.neural_signature)
    self.tick += 1

    tick_payload = SimulationTick(
        tick=self.tick,
        simulation_id=self.simulation_id,
        timestamp=time.time(),
        agents=self.agents,
    )
    await manager.broadcast(self.simulation_id, tick_payload.model_dump_json())

    if manager.active_count(self.simulation_id) == 0:
        zero_client_ticks += 1
        if zero_client_ticks >= ZERO_CLIENT_GRACE_TICKS:
            self.running = False
            break
    else:
        zero_client_ticks = 0

    elapsed = asyncio.get_event_loop().time() - t0
    await asyncio.sleep(max(0.0, TARGET_INTERVAL - elapsed))
```

If no clients are connected for 60 consecutive ticks (~6 seconds), the engine shuts itself down. No orphaned background tasks accumulating memory and CPU. The grace period prevents premature termination during brief reconnections.

---

## TDD: Tests Before Architecture

I built this entire system test-first. 40 backend tests and 21 frontend tests were written *before* the implementation code. This wasn't dogma — it was practical:

- **The WebSocket test caught a Starlette bug**: you must call `accept()` before `close()` on a WebSocket, even when rejecting the connection. The test for "unknown simulation ID returns close code 4004" failed until I added the accept call. I would have shipped that bug without the test.

- **The engine self-termination test caught a mock bug**: `AsyncMock()` makes *every* method return a coroutine when called. But `active_count()` is a synchronous method — calling it without `await` returned a truthy coroutine object, so `== 0` was always `False`, causing an infinite loop. The test hung, which told me exactly where the problem was.

Both bugs would have been painful to debug in production. Both were caught in under a second by the test suite.

---

## What's Next

The mock functions are placeholders with clean swap-in interfaces. The next phase:

1. **Real neural signature extraction** — integrating a video-to-fMRI decoder so the "biological prior" comes from actual model predictions, not random numbers.

2. **Learned swarm dynamics** — replacing the boid rules with a Graph Attention Network trained on real social cascade data.

3. **Temporal interpolation** — lerping between server ticks on the client side for buttery-smooth agent movement.

The architecture is deliberately designed so that plugging in real ML models changes *function bodies only*. No rewiring, no schema changes, no frontend modifications.

---

## Key Takeaways

If you're building real-time data visualization systems, these patterns transfer directly:

- **Never put high-frequency data in React state.** Use `useRef` + `useFrame` for anything updating faster than ~2 FPS.
- **InstancedMesh is non-negotiable** for rendering hundreds+ of similar objects. One draw call vs. N draw calls is the difference between 60 FPS and a slideshow.
- **Decouple your tick rates.** Server computation and client rendering have different performance budgets. A ref buffer is the bridge.
- **Self-terminating background tasks** prevent resource leaks. Always have a "no one is watching" exit condition.
- **Lock-copy-iterate-cleanup** for broadcasting to dynamic connection sets. Never mutate a collection while iterating it.

---

*The Neuro-Social Simulation Engine is an active R&D project. If you're working at the intersection of computational neuroscience and social simulation, I'd love to hear from you.*

---

### Tech Stack

| Layer | Stack |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic v2, numpy, asyncio |
| Frontend | React 18, React Three Fiber, Three.js, Zustand, Vite |
| Testing | pytest (40 tests), Vitest (21 tests), TDD throughout |
| ML (planned) | PyTorch, TRIBE v2, Graph Attention Networks |
