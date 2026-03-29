# Architecture

## System Overview

The Neuro-Social Simulation Engine is a standalone microservice that predicts how multi-modal media biologically resonates with individuals and how that biological response drives viral social network dynamics.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Client (Browser)                             │
│  ┌──────────────┐  ┌──────────────────────────────────────────────┐ │
│  │ ControlPanel │  │           SwarmVisualizer (R3F)              │ │
│  │  (form UI)   │  │  ┌──────────┐   ┌─────────────────────────┐ │ │
│  │              │  │  │ useFrame │──▶│ InstancedMesh (1k agents)│ │ │
│  └──────┬───────┘  │  │  60 FPS  │   │  1 GPU draw call        │ │ │
│         │          │  └────▲─────┘   └─────────────────────────┘ │ │
│         │          │       │ reads                                │ │
│         │          │  agentBufferRef.current                     │ │
│         │          │       ▲ writes (no React state)             │ │
│         │          │  ┌────┴─────────────┐                       │ │
│         │          │  │ useSimulationSocket│ ◄── WS onmessage   │ │
│         │          │  └──────────────────┘                       │ │
│  HUD ◄──Zustand    └──────────────────────────────────────────────┘ │
└────┬────────────────────────────────────┬───────────────────────────┘
     │ POST /api/v1/simulate              │ WS /ws/{sim_id}
     ▼                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (Python)                         │
│                                                                     │
│  POST /api/v1/simulate                                              │
│   ├─ mock_get_neural_signature(url) → dict[str, float]             │
│   ├─ _init_agents(swarm_size) → list[AgentState]                   │
│   ├─ SimulationEngine(id, sig, agents)                             │
│   └─ asyncio.create_task(engine.run(manager))                      │
│                                                                     │
│  SimulationEngine.run()  [background task, ~10 FPS]                │
│   ├─ mock_advance_swarm(agents, sig) → agents   [numpy boid rules] │
│   ├─ SimulationTick → model_dump_json()                            │
│   └─ ConnectionManager.broadcast(sim_id, json)                     │
│                                                                     │
│  WS /ws/{simulation_id}                                            │
│   ├─ ConnectionManager.connect(sim_id, ws)                         │
│   ├─ keepalive receive loop                                        │
│   └─ ConnectionManager.disconnect(sim_id, ws)                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### Backend Modules

| Module | Responsibility |
|---|---|
| `main.py` | FastAPI app, REST endpoint, WebSocket endpoint, agent initialization |
| `models.py` | All Pydantic v2 schemas: `AgentState`, `SimulationRequest/Response`, `SimulationTick` |
| `simulation/mock_neural.py` | Mock TRIBE v2 fMRI extractor — deterministic URL → neural signature |
| `simulation/mock_swarm.py` | Mock MiroFish boid physics — numpy-vectorized with neural weighting |
| `simulation/engine.py` | `SimulationEngine` dataclass — owns one simulation's tick loop + self-termination |
| `ws/manager.py` | `ConnectionManager` — per-sim-id WS set, lock-guarded connect/disconnect/broadcast |

### Frontend Components

| Component | Responsibility |
|---|---|
| `SwarmVisualizer.jsx` | R3F Canvas + `SwarmMesh` inner component (InstancedMesh, useFrame, matrix updates) |
| `ControlPanel.jsx` | Form UI (media URL + swarm size slider) — triggers `startSimulation` |
| `HUD.jsx` | Overlay showing tick count, connection status, neural signature bar chart |
| `simulationStore.js` | Zustand store — UI state only (simulationId, neuralSignature, connectionStatus, tickCount) |
| `useSimulationSocket.js` | Custom hook — WS lifecycle, writes to agentBufferRef, increments tick counter |

## Concurrency Model

The backend runs on a single asyncio event loop (uvicorn):

1. **REST request** — synchronous handler creates engine + `asyncio.create_task`
2. **Background tasks** — each `SimulationEngine.run()` is a long-lived coroutine that `await`s `asyncio.sleep` between ticks. Mock numpy computation is fast (~sub-ms for 1k agents) so it doesn't block the loop.
3. **WebSocket connections** — each connected client runs a keepalive coroutine (`await ws.receive_text()`). Broadcasting is done by the engine's background task via `ConnectionManager.broadcast`.
4. **Lock discipline** — `ConnectionManager._lock` (asyncio.Lock) guards the `_connections` dict to prevent race conditions between connect/disconnect/broadcast coroutines.

### When Real ML Models Are Added

- Wrap blocking GPU inference in `await loop.run_in_executor(None, model_fn, *args)` to keep the event loop responsive.
- For multi-GPU, consider a separate process pool executor.

## Data Flow: REST → WS → GPU

```
1. User clicks "Launch Simulation"
2. ControlPanel → POST /api/v1/simulate { media_url, swarm_size }
3. Backend: mock_get_neural_signature(url) → neural_signature dict
4. Backend: init N agents on sphere surface (radius 20)
5. Backend: SimulationEngine created, asyncio.create_task(engine.run)
6. Response: { simulation_id, swarm_size, neural_signature }
7. Zustand store: sets simulationId → triggers useSimulationSocket hook
8. Hook: opens WS /ws/{simulation_id}
9. Engine loop (every 100ms):
   a. mock_advance_swarm(agents, sig) → updated agents
   b. SimulationTick.model_dump_json() → JSON string
   c. ConnectionManager.broadcast → ws.send_text for all clients
10. Browser ws.onmessage: agentBufferRef.current = JSON.parse(data)
11. useFrame (every ~16ms):
    a. Read agentBufferRef.current.agents
    b. For each agent: Matrix4.setPosition → setMatrixAt + setColorAt
    c. instanceMatrix.needsUpdate = true
    d. GPU: single draw call for all instances
```

## Scale Considerations

- **Horizontal**: Each simulation is isolated (own engine + own WS set). Multiple simulations run concurrently in the same process. For very high simulation counts, deploy multiple backend instances behind a load balancer with sticky sessions (WS affinity).
- **Vertical**: Swarm size up to 5000 agents with numpy mock is sub-ms per tick. With real GNN models, expect 10-100ms per tick — may need to reduce tick rate or batch multiple simulations per GPU.
- **Frontend**: InstancedMesh handles 5000 instances with a single draw call. For 10k+, consider LOD (level of detail) or spatial partitioning to cull off-screen agents.
