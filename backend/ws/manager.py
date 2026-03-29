"""
WebSocket connection manager.

Maintains a per-simulation-id set of active WebSocket connections and
provides thread-safe connect / disconnect / broadcast operations.

A module-level singleton (``manager``) is imported by main.py and
passed to each SimulationEngine so they all share the same connection table.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections grouped by simulation_id.

    An asyncio.Lock guards the connection dict to prevent race conditions
    when coroutines simultaneously connect, disconnect, and broadcast.

    Multiple simulations are fully isolated: broadcasting to "sim-a" will
    never deliver messages to clients connected to "sim-b".
    """

    def __init__(self) -> None:
        # simulation_id → set of active WebSocket connections
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self, simulation_id: str, websocket: WebSocket) -> None:
        """
        Accept *websocket* and register it under *simulation_id*.

        Must be called before any data is read from or written to the socket.
        """
        await websocket.accept()
        async with self._lock:
            if simulation_id not in self._connections:
                self._connections[simulation_id] = set()
            self._connections[simulation_id].add(websocket)
        logger.debug("WS connect: sim=%s total=%d", simulation_id, self.active_count(simulation_id))

    async def disconnect(self, simulation_id: str, websocket: WebSocket) -> None:
        """
        Remove *websocket* from the connection table.

        Cleans up the simulation_id entry when its last client disconnects.
        Safe to call even if *websocket* is not currently registered.
        """
        async with self._lock:
            sockets = self._connections.get(simulation_id, set())
            sockets.discard(websocket)
            if not sockets:
                self._connections.pop(simulation_id, None)
        logger.debug("WS disconnect: sim=%s total=%d", simulation_id, self.active_count(simulation_id))

    # ------------------------------------------------------------------
    # Broadcasting
    # ------------------------------------------------------------------

    async def broadcast(self, simulation_id: str, message: str) -> None:
        """
        Send *message* to every WebSocket connected to *simulation_id*.

        Stale sockets that raise during send are removed from the table
        after the iteration completes (to avoid mutating the set mid-loop).
        """
        async with self._lock:
            sockets = set(self._connections.get(simulation_id, set()))

        stale: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_text(message)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Stale WS removed (sim=%s): %s", simulation_id, exc)
                stale.append(ws)

        if stale:
            async with self._lock:
                active = self._connections.get(simulation_id, set())
                for ws in stale:
                    active.discard(ws)
                if not active:
                    self._connections.pop(simulation_id, None)

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def active_count(self, simulation_id: str) -> int:
        """Return the number of active WebSocket connections for *simulation_id*."""
        return len(self._connections.get(simulation_id, set()))


# Module-level singleton — imported by main.py and simulation/engine.py
manager = ConnectionManager()
