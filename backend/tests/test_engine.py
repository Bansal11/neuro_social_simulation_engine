"""
Tests for backend/simulation/engine.py.
Written before implementation (TDD).
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_agents(n: int = 5) -> list:
    from models import AgentState, AgentStateEnum

    return [
        AgentState(
            id=i, x=float(i), y=0.0, z=0.0,
            vx=0.0, vy=0.0, vz=0.0,
            state=AgentStateEnum.NEUTRAL,
            influence_score=0.0,
        )
        for i in range(n)
    ]


def _make_mock_manager(active_count: int = 1) -> MagicMock:
    """Create a mock ConnectionManager with sync active_count and async broadcast."""
    mgr = MagicMock()
    mgr.active_count = MagicMock(return_value=active_count)
    mgr.broadcast = AsyncMock()
    return mgr


@pytest.fixture
def neural_sig():
    return {
        "ventral_striatum_reward": 0.5,
        "anterior_insula_valence": 0.5,
        "amygdala_arousal": 0.5,
        "prefrontal_cortex_regulation": 0.5,
        "nucleus_accumbens_motivation": 0.5,
        "posterior_superior_temporal_sulcus_social": 0.5,
    }


@pytest.mark.asyncio
async def test_engine_increments_tick(neural_sig):
    """After one run iteration the engine's tick counter should be 1."""
    from simulation.engine import SimulationEngine

    engine = SimulationEngine(
        simulation_id="test-1",
        neural_signature=neural_sig,
        agents=_make_agents(),
    )

    manager = _make_mock_manager(active_count=1)

    async def stop_after_one(sim_id, msg):
        engine.running = False

    manager.broadcast.side_effect = stop_after_one
    await engine.run(manager)

    assert engine.tick == 1


@pytest.mark.asyncio
async def test_engine_broadcasts_tick(neural_sig):
    """manager.broadcast must be called with a non-empty JSON string each iteration."""
    from simulation.engine import SimulationEngine

    engine = SimulationEngine(
        simulation_id="test-2",
        neural_signature=neural_sig,
        agents=_make_agents(),
    )

    manager = _make_mock_manager(active_count=1)
    captured: list[str] = []

    async def capture(sim_id, msg):
        captured.append(msg)
        engine.running = False

    manager.broadcast.side_effect = capture
    await engine.run(manager)

    assert len(captured) == 1
    payload = json.loads(captured[0])
    assert "tick" in payload
    assert "agents" in payload
    assert "simulation_id" in payload


@pytest.mark.asyncio
async def test_engine_tick_payload_is_valid_simulation_tick(neural_sig):
    """Broadcast payload must deserialize into a valid SimulationTick model."""
    from models import SimulationTick
    from simulation.engine import SimulationEngine

    engine = SimulationEngine(
        simulation_id="test-3",
        neural_signature=neural_sig,
        agents=_make_agents(),
    )

    manager = _make_mock_manager(active_count=1)
    broadcast_json: list[str] = []

    async def capture(sim_id, msg):
        broadcast_json.append(msg)
        engine.running = False

    manager.broadcast.side_effect = capture
    await engine.run(manager)

    tick = SimulationTick.model_validate_json(broadcast_json[0])
    assert tick.simulation_id == "test-3"
    assert len(tick.agents) == len(_make_agents())


@pytest.mark.asyncio
async def test_engine_self_terminates(neural_sig):
    """Engine must set running=False when no clients are connected for the grace period."""
    from simulation.engine import ZERO_CLIENT_GRACE_TICKS, SimulationEngine

    engine = SimulationEngine(
        simulation_id="test-4",
        neural_signature=neural_sig,
        agents=_make_agents(),
    )

    manager = _make_mock_manager(active_count=0)  # no clients ever

    # Patch asyncio.sleep inside the engine module to avoid actual waiting
    with patch("simulation.engine.asyncio.sleep", new=AsyncMock()):
        await engine.run(manager)

    assert not engine.running
    # Should have self-terminated after the grace period, not run forever
    assert engine.tick <= ZERO_CLIENT_GRACE_TICKS + 5  # small tolerance
