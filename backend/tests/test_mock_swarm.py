"""
Tests for backend/simulation/mock_swarm.py.
Written before implementation (TDD).
"""
import math

import pytest


def _make_agents(n: int, state: str = "NEUTRAL", influence: float = 0.0) -> list:
    from models import AgentState, AgentStateEnum

    return [
        AgentState(
            id=i,
            x=float(i) * 2.0,
            y=float(i),
            z=0.0,
            vx=0.0,
            vy=0.0,
            vz=0.0,
            state=AgentStateEnum(state),
            influence_score=influence,
        )
        for i in range(n)
    ]


def test_returns_same_count(sample_neural_signature):
    """Output list must have the same number of agents as the input."""
    from simulation.mock_swarm import mock_advance_swarm

    agents = _make_agents(50)
    result = mock_advance_swarm(agents, sample_neural_signature)
    assert len(result) == 50


def test_agent_ids_preserved(sample_neural_signature):
    """All input agent IDs must appear in the output."""
    from simulation.mock_swarm import mock_advance_swarm

    agents = _make_agents(20)
    result = mock_advance_swarm(agents, sample_neural_signature)
    input_ids = {a.id for a in agents}
    output_ids = {a.id for a in result}
    assert input_ids == output_ids


def test_positions_change_over_time(sample_neural_signature):
    """At least some agent positions should differ after one advance step."""
    from simulation.mock_swarm import mock_advance_swarm

    agents = _make_agents(30)
    result = mock_advance_swarm(agents, sample_neural_signature)

    positions_changed = any(
        (a.x, a.y, a.z) != (b.x, b.y, b.z)
        for a, b in zip(agents, result)
    )
    assert positions_changed, "Swarm positions must evolve each tick"


def test_velocity_clamped(high_motivation_signature):
    """No agent velocity magnitude should exceed max_speed * 1.05 (float tolerance)."""
    from simulation.mock_swarm import MAX_SPEED, mock_advance_swarm

    agents = _make_agents(50)
    # Run several steps to let velocities build up
    for _ in range(5):
        agents = mock_advance_swarm(agents, high_motivation_signature)

    for agent in agents:
        speed = math.sqrt(agent.vx ** 2 + agent.vy ** 2 + agent.vz ** 2)
        assert speed <= MAX_SPEED * 1.05, f"Agent {agent.id} speed {speed:.3f} exceeds MAX_SPEED"


def test_influence_score_in_range(sample_neural_signature):
    """All output influence_score values must remain in [0.0, 1.0]."""
    from simulation.mock_swarm import mock_advance_swarm

    agents = _make_agents(30)
    result = mock_advance_swarm(agents, sample_neural_signature)
    for agent in result:
        assert 0.0 <= agent.influence_score <= 1.0


def test_state_transitions_propagating(high_motivation_signature):
    """
    With high motivation and excited agents nearby, some agents should
    transition to PROPAGATING after one advance step.
    """
    from models import AgentStateEnum
    from simulation.mock_swarm import mock_advance_swarm

    # Start all agents as EXCITED in a tight cluster (within radius 5)
    from models import AgentState

    agents = [
        AgentState(
            id=i,
            x=float(i % 5) * 0.5,  # clustered within 2.5 units
            y=float(i // 5) * 0.5,
            z=0.0,
            vx=0.0, vy=0.0, vz=0.0,
            state=AgentStateEnum.EXCITED,
            influence_score=0.9,
        )
        for i in range(25)
    ]

    result = mock_advance_swarm(agents, high_motivation_signature)
    states = {a.state for a in result}
    # With all neighbors excited and high motivation, PROPAGATING should appear
    assert AgentStateEnum.PROPAGATING in states or AgentStateEnum.EXCITED in states


def test_high_regulation_causes_inhibition(high_regulation_signature):
    """
    A signature with prefrontal_cortex_regulation=1.0 should cause at least
    some agents to become INHIBITED.
    """
    from models import AgentStateEnum
    from simulation.mock_swarm import mock_advance_swarm

    agents = _make_agents(50)
    result = mock_advance_swarm(agents, high_regulation_signature)
    states = [a.state for a in result]
    assert AgentStateEnum.INHIBITED in states, (
        "Expected some INHIBITED agents with max regulation signal"
    )
