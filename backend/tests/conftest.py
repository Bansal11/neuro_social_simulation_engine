"""
Shared pytest fixtures for the Neuro-Social Simulation Engine backend tests.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures: domain data
# ---------------------------------------------------------------------------

FMRI_KEYS = [
    "ventral_striatum_reward",
    "anterior_insula_valence",
    "amygdala_arousal",
    "prefrontal_cortex_regulation",
    "nucleus_accumbens_motivation",
    "posterior_superior_temporal_sulcus_social",
]


@pytest.fixture
def sample_neural_signature() -> dict[str, float]:
    """A valid neural signature dict with all 6 fMRI keys, mid-range values."""
    return {key: 0.5 for key in FMRI_KEYS}


@pytest.fixture
def high_motivation_signature() -> dict[str, float]:
    """Signature that strongly activates cohesion / propagation."""
    return {
        "ventral_striatum_reward": 0.9,
        "anterior_insula_valence": 0.3,
        "amygdala_arousal": 0.8,
        "prefrontal_cortex_regulation": 0.1,
        "nucleus_accumbens_motivation": 0.95,
        "posterior_superior_temporal_sulcus_social": 0.9,
    }


@pytest.fixture
def high_regulation_signature() -> dict[str, float]:
    """Signature that drives INHIBITED state transitions."""
    return {
        "ventral_striatum_reward": 0.2,
        "anterior_insula_valence": 0.2,
        "amygdala_arousal": 0.1,
        "prefrontal_cortex_regulation": 1.0,
        "nucleus_accumbens_motivation": 0.1,
        "posterior_superior_temporal_sulcus_social": 0.2,
    }


def make_agents(n: int = 10, state: str = "NEUTRAL") -> list:
    """
    Build a list of AgentState objects. Imported lazily to avoid ImportError
    before models.py exists (tests must be importable even before impl exists).
    """
    from models import AgentState, AgentStateEnum  # noqa: PLC0415

    return [
        AgentState(
            id=i,
            x=float(i),
            y=0.0,
            z=0.0,
            vx=0.0,
            vy=0.0,
            vz=0.0,
            state=AgentStateEnum(state),
            influence_score=0.0,
        )
        for i in range(n)
    ]


@pytest.fixture
def sample_agents() -> list:
    return make_agents(10)


@pytest.fixture
def excited_agents() -> list:
    return make_agents(20, state="EXCITED")


# ---------------------------------------------------------------------------
# Fixtures: application client
# ---------------------------------------------------------------------------

@pytest.fixture
def app_client():
    """Synchronous FastAPI TestClient (httpx-backed)."""
    from main import app  # noqa: PLC0415

    with TestClient(app) as client:
        yield client


# ---------------------------------------------------------------------------
# Fixtures: mock WebSocket
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_websocket():
    """A mock WebSocket that records sent messages."""
    ws = AsyncMock()
    ws.sent_messages: list[str] = []

    async def _send_text(msg: str) -> None:
        ws.sent_messages.append(msg)

    ws.send_text.side_effect = _send_text
    return ws


@pytest.fixture
def mock_manager():
    """A mock ConnectionManager for unit tests that bypass real WebSockets."""
    from ws.manager import ConnectionManager  # noqa: PLC0415

    mgr = AsyncMock(spec=ConnectionManager)
    mgr.active_count.return_value = 1  # default: one client connected
    return mgr
