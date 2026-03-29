"""
Tests for backend/models.py.
Written before implementation (TDD — expect failures until models.py exists).
"""
import pytest
from pydantic import ValidationError


def test_agent_state_enum_values():
    """All five biological states must be defined."""
    from models import AgentStateEnum

    assert set(AgentStateEnum.__members__) == {
        "NEUTRAL",
        "EXCITED",
        "INHIBITED",
        "PROPAGATING",
        "EXHAUSTED",
    }


def test_agent_state_serializes_state_as_string():
    """model_dump() must return a plain string for 'state', not an enum object."""
    from models import AgentState, AgentStateEnum

    agent = AgentState(
        id=0, x=1.0, y=2.0, z=3.0,
        vx=0.0, vy=0.0, vz=0.0,
        state=AgentStateEnum.EXCITED,
        influence_score=0.5,
    )
    dumped = agent.model_dump()
    assert isinstance(dumped["state"], str), "state should serialize as a plain string"
    assert dumped["state"] == "EXCITED"


def test_simulation_request_swarm_size_lower_bound():
    """swarm_size=0 must fail validation."""
    from models import SimulationRequest

    with pytest.raises(ValidationError):
        SimulationRequest(media_url="https://example.com/video", swarm_size=0)


def test_simulation_request_swarm_size_upper_bound():
    """swarm_size=5001 must fail validation."""
    from models import SimulationRequest

    with pytest.raises(ValidationError):
        SimulationRequest(media_url="https://example.com/video", swarm_size=5001)


def test_simulation_request_default_swarm_size():
    """swarm_size should default to 500."""
    from models import SimulationRequest

    req = SimulationRequest(media_url="https://example.com/video")
    assert req.swarm_size == 500


def test_simulation_tick_json_round_trip(sample_neural_signature, sample_agents):
    """Serializing then deserializing a SimulationTick preserves all data."""
    import time
    from models import SimulationTick

    tick = SimulationTick(
        tick=42,
        simulation_id="abc-123",
        timestamp=time.time(),
        agents=sample_agents,
    )
    json_str = tick.model_dump_json()
    restored = SimulationTick.model_validate_json(json_str)

    assert restored.tick == 42
    assert restored.simulation_id == "abc-123"
    assert len(restored.agents) == len(sample_agents)
    assert restored.agents[0].id == sample_agents[0].id


def test_agent_state_influence_score_lower_bound():
    """influence_score < 0.0 must fail validation."""
    from models import AgentState, AgentStateEnum

    with pytest.raises(ValidationError):
        AgentState(
            id=0, x=0.0, y=0.0, z=0.0,
            vx=0.0, vy=0.0, vz=0.0,
            state=AgentStateEnum.NEUTRAL,
            influence_score=-0.1,
        )


def test_agent_state_influence_score_upper_bound():
    """influence_score > 1.0 must fail validation."""
    from models import AgentState, AgentStateEnum

    with pytest.raises(ValidationError):
        AgentState(
            id=0, x=0.0, y=0.0, z=0.0,
            vx=0.0, vy=0.0, vz=0.0,
            state=AgentStateEnum.NEUTRAL,
            influence_score=1.1,
        )
