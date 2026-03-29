# WebSocket Protocol

## Overview

The WebSocket endpoint `WS /ws/{simulation_id}` streams `SimulationTick` JSON
messages to connected clients at approximately 10 frames per second. The
protocol is unidirectional: the server sends tick data, clients receive it.

## SimulationTick Schema

Each message is a single JSON object:

```json
{
  "tick": 42,
  "simulation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": 1711720800.123456,
  "agents": [
    {
      "id": 0,
      "x": 12.34,
      "y": -5.67,
      "z": 8.90,
      "vx": 0.12,
      "vy": -0.34,
      "vz": 0.05,
      "state": "EXCITED",
      "influence_score": 0.82
    }
  ]
}
```

### Top-level fields

| Field | Type | Description |
|---|---|---|
| `tick` | integer | Monotonically increasing counter (starts at 1) |
| `simulation_id` | string | UUID of the parent simulation |
| `timestamp` | float | Unix epoch (seconds) when the tick was generated server-side |
| `agents` | array | Full swarm state — one entry per agent |

### AgentState fields

| Field | Type | Range | Description |
|---|---|---|---|
| `id` | integer | 0 – N-1 | Unique agent identifier within the simulation |
| `x` | float | unbounded | Position — x axis (simulation units) |
| `y` | float | unbounded | Position — y axis |
| `z` | float | unbounded | Position — z axis |
| `vx` | float | bounded by MAX_SPEED | Velocity — x component |
| `vy` | float | bounded by MAX_SPEED | Velocity — y component |
| `vz` | float | bounded by MAX_SPEED | Velocity — z component |
| `state` | string (enum) | see below | Current biological state |
| `influence_score` | float | [0.0, 1.0] | How strongly this agent influences its local neighbourhood |

## AgentStateEnum

| Value | Biological Interpretation | Visual Color |
|---|---|---|
| `NEUTRAL` | Baseline low-activation resting state. Agent follows normal boid dynamics. | Blue `#4a90d9` |
| `EXCITED` | High dopaminergic / reward-driven activity. Agent has been stimulated by media resonance or neighbour influence. | Orange-red `#e8511a` |
| `INHIBITED` | Prefrontal down-regulation of excitation. The prefrontal cortex regulation signal suppresses the agent's reactivity. | Purple `#6a4c93` |
| `PROPAGATING` | Spreading activation. Agent actively transmits its excitation to neighbouring agents — the viral cascade mechanism. | Yellow `#f7b731` |
| `EXHAUSTED` | Post-excitation refractory period. Agent has been EXCITED too long (>30 ticks) and enters a cooldown state. | Grey `#808080` |

### State Transition Rules

```
                          ┌──────────────┐
                          │   NEUTRAL    │ ◄── default / reset
                          └──────┬───────┘
                                 │ influence_score > 0.7
                                 ▼
                          ┌──────────────┐
                     ┌───▶│   EXCITED    │───┐
                     │    └──────────────┘   │ >30 ticks
                     │           │           ▼
     excited neighbour           │    ┌──────────────┐
     + motivation > 0.6         │    │  EXHAUSTED   │──▶ NEUTRAL
                     │           │    └──────────────┘
                     │           ▼
                     │    ┌──────────────┐
                     └────│ PROPAGATING  │
                          └──────────────┘
                                 │
          regulation > 0.8       │ (override — any state)
                                 ▼
                          ┌──────────────┐
                          │  INHIBITED   │
                          └──────────────┘
```

## Message Rate

- Server target: **10 FPS** (one tick every 100ms)
- Actual rate may vary depending on swarm size and server load
- Clients should tolerate variable frame pacing

## Keepalive

The client may send any text frame to keep the connection alive. The server
does not respond or echo. This is useful when load balancers or proxies
enforce idle connection timeouts.

## Connection Lifecycle

```
Client                              Server
  │                                   │
  │ ──── WS upgrade request ────────▶ │
  │                                   │ look up simulation_id
  │ ◀──── accept (or close 4004) ──── │
  │                                   │
  │ ◀──── SimulationTick (tick 1) ─── │
  │ ◀──── SimulationTick (tick 2) ─── │
  │ ◀──── SimulationTick (tick 3) ─── │
  │ ...                               │ ~10 FPS
  │                                   │
  │ ──── close frame ────────────────▶ │
  │                                   │ manager.disconnect
  │ ◀──── close ACK ──────────────── │
```
