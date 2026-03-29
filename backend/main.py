"""
Neuro-Social Simulation Engine — FastAPI application entry point.

Routes:
    POST /api/v1/simulate   Start a new simulation run.
    WS   /ws/{sim_id}       Stream SimulationTick payloads to a client.

Usage:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import asyncio
import logging
import uuid

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState

from models import AgentState, AgentStateEnum, SimulationRequest, SimulationResponse
from simulation.engine import SimulationEngine, get_engine, prune_stopped_engines, register_engine
from simulation.mock_neural import mock_get_neural_signature
from ws.manager import manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Neuro-Social Simulation Engine",
    description=(
        "Bridges in-silico neuroscience (TRIBE v2 fMRI predictions) with social swarm "
        "simulation (MiroFish multi-agent system). Streams real-time agent states via WebSocket."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restrict to deployed frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _init_agents(swarm_size: int) -> list[AgentState]:
    """
    Spawn *swarm_size* agents distributed uniformly on the surface of a sphere
    of radius 20, with zero initial velocity and NEUTRAL state.
    """
    rng = np.random.default_rng()

    # Uniform sphere sampling via rejection or Marsaglia method
    xyz = rng.standard_normal((swarm_size, 3)).astype(np.float32)
    norms = np.linalg.norm(xyz, axis=1, keepdims=True)
    xyz = xyz / norms * 20.0  # radius = 20

    return [
        AgentState(
            id=i,
            x=float(xyz[i, 0]),
            y=float(xyz[i, 1]),
            z=float(xyz[i, 2]),
            vx=0.0,
            vy=0.0,
            vz=0.0,
            state=AgentStateEnum.NEUTRAL,
            influence_score=0.0,
        )
        for i in range(swarm_size)
    ]


# ---------------------------------------------------------------------------
# REST endpoint
# ---------------------------------------------------------------------------

@app.post("/api/v1/simulate", response_model=SimulationResponse)
async def start_simulation(request: SimulationRequest) -> SimulationResponse:
    """
    Start a new simulation run.

    Steps:
    1. Extract a neural signature from *media_url* (mock or real TRIBE v2).
    2. Initialise the swarm on a sphere.
    3. Create a SimulationEngine and launch its run loop as a background task.
    4. Return the simulation_id for the client to open the WebSocket stream.
    """
    prune_stopped_engines()

    # 1. Neural signature
    neural_signature = mock_get_neural_signature(request.media_url)
    logger.info("Neural signature extracted for %s", request.media_url)

    # 2. Initial swarm state
    agents = _init_agents(request.swarm_size)

    # 3. Engine + background task
    simulation_id = str(uuid.uuid4())
    engine = SimulationEngine(
        simulation_id=simulation_id,
        neural_signature=neural_signature,
        agents=agents,
    )
    register_engine(engine)
    asyncio.create_task(engine.run(manager), name=f"sim-{simulation_id}")
    logger.info("Simulation started: id=%s swarm_size=%d", simulation_id, request.swarm_size)

    return SimulationResponse(
        simulation_id=simulation_id,
        swarm_size=request.swarm_size,
        neural_signature=neural_signature,
    )


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@app.websocket("/ws/{simulation_id}")
async def websocket_stream(websocket: WebSocket, simulation_id: str) -> None:
    """
    Stream SimulationTick payloads for *simulation_id* to the connecting client.

    Close code 4004 is sent if the simulation_id is unknown.
    The client may send any text frame (e.g. "ping") to keep the connection
    alive; the server does not echo it (one-way stream).
    """
    engine = get_engine(simulation_id)
    if engine is None:
        await websocket.close(code=4004, reason="Unknown simulation_id")
        return

    await manager.connect(simulation_id, websocket)
    logger.info("WS client connected: sim=%s", simulation_id)

    try:
        # Keep the connection open until the client disconnects.
        # The simulation engine broadcasts independently via manager.broadcast.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(simulation_id, websocket)
        logger.info("WS client disconnected: sim=%s", simulation_id)
