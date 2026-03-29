"""
Tests for backend/ws/manager.py.
Written before implementation (TDD).
"""
import asyncio
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def manager():
    """Fresh ConnectionManager for each test (avoids shared state)."""
    from ws.manager import ConnectionManager

    return ConnectionManager()


async def _make_ws() -> AsyncMock:
    """Helper: create a mock WebSocket that has already been accepted."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_connect_increments_active_count(manager):
    ws = await _make_ws()
    await manager.connect("sim-1", ws)
    assert manager.active_count("sim-1") == 1


@pytest.mark.asyncio
async def test_disconnect_decrements_active_count(manager):
    ws = await _make_ws()
    await manager.connect("sim-1", ws)
    await manager.disconnect("sim-1", ws)
    assert manager.active_count("sim-1") == 0


@pytest.mark.asyncio
async def test_disconnect_removes_empty_sim_entry(manager):
    """After last client disconnects, the simulation_id key is removed from the dict."""
    ws = await _make_ws()
    await manager.connect("sim-1", ws)
    await manager.disconnect("sim-1", ws)
    # Internal dict should not hold an empty set
    assert "sim-1" not in manager._connections


@pytest.mark.asyncio
async def test_broadcast_sends_to_all_connected(manager):
    """All connected WebSockets for a simulation_id must receive the broadcast."""
    ws1, ws2, ws3 = await _make_ws(), await _make_ws(), await _make_ws()
    for ws in (ws1, ws2, ws3):
        await manager.connect("sim-1", ws)

    await manager.broadcast("sim-1", '{"tick": 1}')

    for ws in (ws1, ws2, ws3):
        ws.send_text.assert_called_once_with('{"tick": 1}')


@pytest.mark.asyncio
async def test_broadcast_removes_stale_socket(manager):
    """A WebSocket that raises on send_text must be removed after the broadcast."""
    good_ws = await _make_ws()
    bad_ws = await _make_ws()
    bad_ws.send_text.side_effect = RuntimeError("connection lost")

    await manager.connect("sim-1", good_ws)
    await manager.connect("sim-1", bad_ws)

    # Should not raise; stale socket handled gracefully
    await manager.broadcast("sim-1", "data")

    assert manager.active_count("sim-1") == 1
    good_ws.send_text.assert_called_once()


@pytest.mark.asyncio
async def test_active_count_unknown_sim_returns_zero(manager):
    """active_count for an unknown simulation_id must return 0, not raise."""
    assert manager.active_count("nonexistent") == 0


@pytest.mark.asyncio
async def test_multiple_simulations_are_isolated(manager):
    """Connections for different simulation IDs must not interfere."""
    ws_a = await _make_ws()
    ws_b = await _make_ws()
    await manager.connect("sim-a", ws_a)
    await manager.connect("sim-b", ws_b)

    await manager.broadcast("sim-a", "msg-a")

    ws_a.send_text.assert_called_once_with("msg-a")
    ws_b.send_text.assert_not_called()
