# Social Media Posts

## LinkedIn Post

---

**I built an engine that gives AI agents a nervous system.**

The idea: what if you could predict whether content would go viral — not from engagement metrics, but by simulating how it biologically resonates with people?

The Neuro-Social Simulation Engine extracts a "neural signature" from media (predicted fMRI activations across 6 brain regions), then injects that signature into 1,000+ AI agents as a biological prior. The agents interact, excite each other, propagate activation, and self-organize — all in real time.

Three architecture decisions made this work:

**1. Biological state machine**
Each agent has 5 neural states: NEUTRAL → EXCITED → PROPAGATING → EXHAUSTED (with INHIBITED as a regulation override). Real neurons have refractory periods. Real cascades have saturation. Encoding this into agent behaviour produces emergent dynamics that feel right.

**2. The 10/60 FPS decoupling trick**
The server computes swarm physics at 10 FPS. The 3D client renders at 60 FPS. The bridge? A `useRef` buffer — WebSocket data never touches React state. The `useFrame` loop reads from the ref and updates 1,000 InstancedMesh transforms in a single GPU draw call. Zero re-renders on the hot path.

**3. Self-healing WebSocket infrastructure**
Lock-copy-iterate-cleanup pattern for broadcasting. Self-terminating simulation engines (no orphaned tasks). Stale socket detection and removal during broadcast. Production-grade from day one.

Built TDD — 40 backend + 21 frontend tests written before the implementation. Two real bugs caught by tests before they ever ran in a browser.

Stack: FastAPI + WebSockets | React Three Fiber + InstancedMesh | Pydantic v2 | numpy | Zustand

Next: replacing mocks with real neuroscience models (video → fMRI decoder) and a Graph Attention Network for learned swarm dynamics.

Full architecture deep-dive on Medium (link in comments).

#AI #Neuroscience #WebSockets #ReactThreeFiber #Python #FastAPI #SystemDesign #TDD

---

## X (Twitter) Thread

---

**Tweet 1 (hook):**

I built an engine that gives AI agents a nervous system.

It extracts predicted brain activations from media, injects them into 1,000 swarm agents, and simulates how the social cascade unfolds in real time.

Here's the architecture that makes it work at 60 FPS 🧵

---

**Tweet 2 (the concept):**

The idea: media → neural signature (6 brain regions scored 0-1) → biological prior for agent swarm.

Different content produces genuinely different emergent behaviour. High reward + low regulation = explosive viral cascade. High regulation = suppressed spread.

Biology drives the simulation.

---

**Tweet 3 (the performance trick):**

The hardest problem: server runs at 10 FPS, client needs 60 FPS.

Solution: WebSocket data NEVER touches React state.

```
ws.onmessage = (e) => {
  agentBufferRef.current = JSON.parse(e.data)
}
```

useRef buffer → useFrame reads at 60fps → InstancedMesh → 1 GPU draw call for 1,000 agents.

---

**Tweet 4 (the state machine):**

Each agent has a biological state machine:

NEUTRAL → EXCITED → PROPAGATING → EXHAUSTED

With INHIBITED as a regulation override.

Real neurons have refractory periods. Real cascades saturate. Encoding this produces emergent dynamics that feel biologically real.

---

**Tweet 5 (TDD win):**

Built the whole thing TDD. 61 tests before implementation.

Two bugs caught that would've been painful in prod:

1. Starlette requires accept() before close() on WebSocket rejection
2. AsyncMock makes sync methods return coroutines — caused an infinite loop

Both found in <1 second by test suite.

---

**Tweet 6 (stack + CTA):**

Stack:
- FastAPI + WebSockets (backend)
- React Three Fiber + InstancedMesh (3D)
- Pydantic v2 (schemas)
- numpy (swarm physics)
- Zustand (UI state)

Next: real neuroscience models replacing the mocks.

Full deep-dive on Medium → [link]

---
