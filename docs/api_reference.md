# API Reference

Base URL: `http://localhost:8000` (development)

## REST Endpoints

### POST /api/v1/simulate

Start a new simulation run. Extracts a neural signature from the media URL,
initializes the swarm, and launches the simulation engine as a background task.

**Request body** (`application/json`):

```json
{
  "media_url": "https://example.com/travel-video.mp4",
  "swarm_size": 500
}
```

| Field | Type | Required | Default | Constraints |
|---|---|---|---|---|
| `media_url` | string | yes | — | Any URL string |
| `swarm_size` | integer | no | 500 | 1 – 5000 |

**Response** (`200 OK`):

```json
{
  "simulation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "swarm_size": 500,
  "neural_signature": {
    "ventral_striatum_reward": 0.72,
    "anterior_insula_valence": 0.45,
    "amygdala_arousal": 0.81,
    "prefrontal_cortex_regulation": 0.33,
    "nucleus_accumbens_motivation": 0.68,
    "posterior_superior_temporal_sulcus_social": 0.57
  }
}
```

| Field | Type | Description |
|---|---|---|
| `simulation_id` | string (UUID) | Use this to open the WebSocket stream |
| `swarm_size` | integer | Number of agents spawned |
| `neural_signature` | object | Predicted fMRI activations per brain region (all values in [0, 1]) |

**Error responses**:

| Status | Reason |
|---|---|
| `422` | Validation error (missing `media_url`, `swarm_size` out of bounds, etc.) |
| `500` | Internal server error |

**Example** (curl):

```bash
curl -X POST http://localhost:8000/api/v1/simulate \
  -H "Content-Type: application/json" \
  -d '{"media_url": "https://youtube.com/watch?v=abc", "swarm_size": 200}'
```

---

## WebSocket Endpoint

### WS /ws/{simulation_id}

Stream real-time `SimulationTick` payloads for a running simulation.

**Connection**:

```
ws://localhost:8000/ws/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Lifecycle**:

1. Client connects with the `simulation_id` from the POST response.
2. Server accepts the connection and registers it with the `ConnectionManager`.
3. Server streams JSON messages at ~10 FPS (one per simulation tick).
4. Client may send any text frame (e.g., `"ping"`) to keep the connection alive. Server does not echo or respond — this is a one-way stream.
5. Connection closes when the client disconnects or the simulation engine self-terminates.

**Close codes**:

| Code | Reason |
|---|---|
| `4004` | Unknown `simulation_id` (no active simulation with that ID) |
| `1000` | Normal closure |
| `1001` | Server shutting down |

**Message format**: See [WebSocket Protocol](websocket_protocol.md) for the full `SimulationTick` schema.

**Example** (wscat):

```bash
# Start simulation
SIM_ID=$(curl -s -X POST http://localhost:8000/api/v1/simulate \
  -H "Content-Type: application/json" \
  -d '{"media_url":"https://example.com/video","swarm_size":100}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['simulation_id'])")

# Connect to WebSocket stream
wscat -c "ws://localhost:8000/ws/$SIM_ID"
```
