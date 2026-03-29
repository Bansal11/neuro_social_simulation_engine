# Neuro-Social Simulation Engine

A standalone microservice that bridges in-silico neuroscience with social swarm simulation. It predicts how multi-modal media (e.g., travel videos) biologically resonates with individuals, and how that biological response drives viral social network dynamics.

## How It Works

1. **Neural Signature Extraction** — A media URL is processed through a neural model (TRIBE v2, currently mocked) to produce predicted fMRI activations across 6 brain regions (reward, valence, arousal, regulation, motivation, social cognition).

2. **Swarm Simulation** — The neural signature is injected as a "biological prior" into a MiroFish multi-agent swarm (currently mocked with numpy boid physics). Each agent's behaviour — separation, alignment, cohesion, state transitions — is weighted by the neural activations.

3. **Real-Time Visualization** — Agent states stream over WebSocket at ~10 FPS. The React Three Fiber client renders 1,000+ agents as an InstancedMesh at 60 FPS, decoupled from the server tick rate via a ref buffer (zero React state updates on the hot path).

## Quick Start

### Backend

```bash
cd backend
pip install -e ".[dev]"
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

Enter a media URL, set the swarm size, and click **Launch Simulation**.

## Running Tests

```bash
# Backend (40 tests)
cd backend && python -m pytest tests/ -v

# Frontend (21 tests)
cd frontend && npm test
```

## Architecture

```
POST /api/v1/simulate → neural signature → init agents → background engine
                                                              ↓ 10 FPS
WS /ws/{sim_id} ← ConnectionManager.broadcast ← SimulationTick
                                                              ↓
Browser: agentBufferRef.current = JSON.parse(data)  [no re-render]
                                                              ↓ 60 FPS
useFrame: Matrix4.setPosition → InstancedMesh → 1 GPU draw call
```

See [docs/architecture.md](docs/architecture.md) for full system design.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic v2, numpy, asyncio |
| Frontend | React 18, React Three Fiber, Three.js, Zustand, TailwindCSS, Vite |
| ML (planned) | PyTorch, TRIBE v2, Graph Attention Networks |

## Documentation

- [Architecture](docs/architecture.md) — System design, data flow, concurrency model
- [API Reference](docs/api_reference.md) — REST + WebSocket endpoint specifications
- [WebSocket Protocol](docs/websocket_protocol.md) — SimulationTick schema, agent states, lifecycle
- [ML Integration Guide](docs/ml_integration_guide.md) — How to swap mock functions with real models

## Project Structure

```
backend/
  main.py                  FastAPI app, REST + WebSocket endpoints
  models.py                Pydantic v2 schemas
  simulation/
    engine.py              SimulationEngine (10 FPS async loop)
    mock_neural.py         Mock TRIBE v2 neural signature extractor
    mock_swarm.py          Mock boid physics with neural weighting
  ws/
    manager.py             WebSocket connection manager
  tests/                   40 pytest tests (models, API, WS, engine, mocks)

frontend/
  src/
    App.jsx                Root layout
    store/
      simulationStore.js   Zustand store (UI state only)
    hooks/
      useSimulationSocket.js   WebSocket hook (writes to ref, not state)
    components/
      SwarmVisualizer.jsx  R3F InstancedMesh + useFrame (performance-critical)
      ControlPanel.jsx     Launch form
      HUD.jsx              Tick counter + neural signature bars
```
