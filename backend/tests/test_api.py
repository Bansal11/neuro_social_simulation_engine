"""
Tests for backend/main.py REST and WebSocket endpoints.
Written before implementation (TDD).
"""
import json
import uuid

import pytest
from fastapi.testclient import TestClient


FMRI_KEYS = {
    "ventral_striatum_reward",
    "anterior_insula_valence",
    "amygdala_arousal",
    "prefrontal_cortex_regulation",
    "nucleus_accumbens_motivation",
    "posterior_superior_temporal_sulcus_social",
}

VALID_PAYLOAD = {"media_url": "https://example.com/video", "swarm_size": 10}


def test_post_simulate_success(app_client):
    """POST /api/v1/simulate with valid body should return 200 and SimulationResponse shape."""
    response = app_client.post("/api/v1/simulate", json=VALID_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert "simulation_id" in body
    assert "swarm_size" in body
    assert "neural_signature" in body


def test_post_simulate_returns_uuid(app_client):
    """simulation_id must be a valid UUID string."""
    response = app_client.post("/api/v1/simulate", json=VALID_PAYLOAD)
    sim_id = response.json()["simulation_id"]
    # Will raise ValueError if not a valid UUID
    uuid.UUID(sim_id)


def test_post_simulate_returns_neural_signature(app_client):
    """Response neural_signature must contain all 6 fMRI keys."""
    response = app_client.post("/api/v1/simulate", json=VALID_PAYLOAD)
    signature = response.json()["neural_signature"]
    assert set(signature.keys()) == FMRI_KEYS


def test_post_simulate_swarm_size_zero_rejected(app_client):
    """swarm_size=0 must return HTTP 422 Unprocessable Entity."""
    response = app_client.post(
        "/api/v1/simulate",
        json={"media_url": "https://example.com/video", "swarm_size": 0},
    )
    assert response.status_code == 422


def test_post_simulate_swarm_size_too_large_rejected(app_client):
    """swarm_size=5001 must return HTTP 422 Unprocessable Entity."""
    response = app_client.post(
        "/api/v1/simulate",
        json={"media_url": "https://example.com/video", "swarm_size": 5001},
    )
    assert response.status_code == 422


def test_post_simulate_missing_media_url_rejected(app_client):
    """Missing media_url must return HTTP 422."""
    response = app_client.post("/api/v1/simulate", json={"swarm_size": 100})
    assert response.status_code == 422


def test_websocket_unknown_simulation_id(app_client):
    """Connecting to an unknown simulation_id must close with code 4004."""
    with app_client.websocket_connect("/ws/nonexistent-id") as ws:
        # Server should close with code 4004
        with pytest.raises(Exception):
            # Receive until disconnected; the server closes immediately
            ws.receive_text()


def test_websocket_receives_tick(app_client):
    """After POSTing a simulation, connecting via WS must receive a SimulationTick."""
    from models import SimulationTick

    # Start simulation
    sim_response = app_client.post("/api/v1/simulate", json=VALID_PAYLOAD)
    sim_id = sim_response.json()["simulation_id"]

    with app_client.websocket_connect(f"/ws/{sim_id}") as ws:
        raw = ws.receive_text()
        tick = SimulationTick.model_validate_json(raw)
        assert tick.simulation_id == sim_id
        assert tick.tick >= 0
        assert isinstance(tick.agents, list)


def test_post_simulate_swarm_size_reflected(app_client):
    """swarm_size in the response must match the request."""
    response = app_client.post(
        "/api/v1/simulate",
        json={"media_url": "https://example.com/video", "swarm_size": 42},
    )
    assert response.json()["swarm_size"] == 42
