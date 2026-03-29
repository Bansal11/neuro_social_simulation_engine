"""
Simulation engine — owns the lifecycle of a single simulation run.

Each simulation gets its own SimulationEngine instance that runs as an
asyncio background task (started by main.py via asyncio.create_task).
The engine advances the swarm at ~10 FPS and broadcasts each tick to all
connected WebSocket clients via the ConnectionManager.

Self-termination: the engine stops automatically after ZERO_CLIENT_GRACE_TICKS
consecutive ticks with no connected clients to prevent orphaned tasks.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

from models import AgentState, SimulationTick
from simulation.mock_swarm import mock_advance_swarm
from ws.manager import ConnectionManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Target tick rate (10 FPS).
TARGET_INTERVAL: float = 1.0 / 10.0

#: Number of consecutive ticks with zero clients before the engine shuts down.
ZERO_CLIENT_GRACE_TICKS: int = 60


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

@dataclass
class SimulationEngine:
    """
    Drives one simulation run.

    Attributes:
        simulation_id: UUID string identifying this run.
        neural_signature: fMRI activation dict from mock_neural (or TRIBE v2).
        agents: Current swarm state (mutated each tick).
        tick: Monotonically increasing counter, starts at 0.
        running: Set to False to stop the run loop from outside.
    """

    simulation_id: str
    neural_signature: dict[str, float]
    agents: list[AgentState]
    tick: int = 0
    running: bool = True

    async def run(self, manager: ConnectionManager) -> None:
        """
        Main simulation loop.  Advances the swarm, broadcasts ticks, and
        self-terminates when no clients are connected for the grace period.

        Args:
            manager: The shared ConnectionManager used for broadcasting.
        """
        zero_client_ticks = 0
        logger.info("SimulationEngine started: sim=%s agents=%d", self.simulation_id, len(self.agents))

        while self.running:
            t0 = asyncio.get_event_loop().time()

            # 1. Advance physics
            self.agents = mock_advance_swarm(self.agents, self.neural_signature)
            self.tick += 1

            # 2. Broadcast to connected clients
            tick_payload = SimulationTick(
                tick=self.tick,
                simulation_id=self.simulation_id,
                timestamp=time.time(),
                agents=self.agents,
            )
            await manager.broadcast(self.simulation_id, tick_payload.model_dump_json())

            # 3. Self-termination: count consecutive ticks with no clients
            if manager.active_count(self.simulation_id) == 0:
                zero_client_ticks += 1
                if zero_client_ticks >= ZERO_CLIENT_GRACE_TICKS:
                    logger.info(
                        "SimulationEngine self-terminating (no clients): sim=%s ticks=%d",
                        self.simulation_id,
                        self.tick,
                    )
                    self.running = False
                    break
            else:
                zero_client_ticks = 0

            # 4. Pace to TARGET_INTERVAL (10 FPS)
            elapsed = asyncio.get_event_loop().time() - t0
            await asyncio.sleep(max(0.0, TARGET_INTERVAL - elapsed))

        logger.info("SimulationEngine stopped: sim=%s total_ticks=%d", self.simulation_id, self.tick)


# ---------------------------------------------------------------------------
# Registry of active engines (keyed by simulation_id)
# ---------------------------------------------------------------------------

_active_engines: dict[str, SimulationEngine] = {}


def register_engine(engine: SimulationEngine) -> None:
    """Add *engine* to the active registry."""
    _active_engines[engine.simulation_id] = engine


def get_engine(simulation_id: str) -> SimulationEngine | None:
    """Return the engine for *simulation_id*, or None if it does not exist."""
    return _active_engines.get(simulation_id)


def prune_stopped_engines() -> None:
    """Remove engines that have finished running from the registry."""
    stopped = [sid for sid, eng in _active_engines.items() if not eng.running]
    for sid in stopped:
        del _active_engines[sid]
