# ML Integration Guide

This guide describes how to replace the mock functions with real ML models.
The system was designed so that integration requires changing **function bodies
only** — all signatures, data contracts, and wiring remain stable.

## Step 1: Replace Neural Signature Extractor (TRIBE v2)

**File**: `backend/simulation/mock_neural.py`

**Current mock**: Hashes the URL string to produce deterministic random activations.

**Target**: Meta's TRIBE v2 (or equivalent) video/audio → fMRI decoder model.

### Contract

```python
def mock_get_neural_signature(media_url: str) -> dict[str, float]:
    """
    Input:  media_url — URL pointing to a video, audio, or image file.
    Output: dict mapping fMRI region names to activation scores in [0.0, 1.0].

    Required keys (the swarm physics depends on these exact names):
      - ventral_striatum_reward
      - anterior_insula_valence
      - amygdala_arousal
      - prefrontal_cortex_regulation
      - nucleus_accumbens_motivation
      - posterior_superior_temporal_sulcus_social
    """
```

### Implementation Steps

1. Download the media from `media_url` (consider caching to disk)
2. Preprocess into model input format (video frames, audio spectrogram, etc.)
3. Run TRIBE v2 inference → raw fMRI activation predictions
4. Map/normalize activations to the 6 required region keys in [0.0, 1.0]
5. Return the dict

### Example Skeleton

```python
import torch
from tribe_v2 import TRIBEModel, preprocess_video

_model = None

def _get_model():
    global _model
    if _model is None:
        _model = TRIBEModel.from_pretrained("meta/tribe-v2-base")
        _model.eval()
        if torch.cuda.is_available():
            _model = _model.cuda()
    return _model

def mock_get_neural_signature(media_url: str) -> dict[str, float]:
    model = _get_model()
    frames = preprocess_video(media_url)
    with torch.no_grad():
        activations = model(frames)
    # Map model output indices to our 6 regions
    return {
        "ventral_striatum_reward": float(activations[0, 12].clip(0, 1)),
        "anterior_insula_valence": float(activations[0, 34].clip(0, 1)),
        # ... etc.
    }
```

---

## Step 2: Replace Swarm Physics (GNN / MiroFish)

**File**: `backend/simulation/mock_swarm.py`

**Current mock**: Numpy-vectorized boid rules with neural signature weighting.

**Target**: Graph Attention Network (GAT) or similar GNN that models agent-to-agent
influence as a learned function.

### Contract

```python
def mock_advance_swarm(
    agents: list[AgentState],
    neural_signature: dict[str, float],
) -> list[AgentState]:
    """
    Input:
      - agents: current swarm state (list of AgentState Pydantic models)
      - neural_signature: dict of 6 fMRI activation scores in [0, 1]

    Output: updated list of AgentState (same length, same IDs)

    Each output AgentState must have:
      - Updated x, y, z, vx, vy, vz (positions and velocities)
      - Updated state (AgentStateEnum value as string)
      - Updated influence_score in [0.0, 1.0]
    """
```

### Implementation Steps

1. Convert `list[AgentState]` → model input tensors (positions, velocities, states, edges)
2. Build adjacency/edge graph (e.g., k-nearest neighbours or radius graph)
3. Inject `neural_signature` values as global conditioning features
4. Run GNN forward pass → predicted next-state per agent
5. Convert output tensors back to `list[AgentState]`

### Example Skeleton (PyTorch Geometric)

```python
import torch
from torch_geometric.data import Data
from torch_geometric.nn import GATv2Conv

class SwarmGNN(torch.nn.Module):
    def __init__(self, in_channels=13, hidden=64, out_channels=10):
        super().__init__()
        self.conv1 = GATv2Conv(in_channels, hidden, heads=4)
        self.conv2 = GATv2Conv(hidden * 4, out_channels, heads=1)

    def forward(self, data):
        x = self.conv1(data.x, data.edge_index).relu()
        return self.conv2(x, data.edge_index)

_model = None

def mock_advance_swarm(agents, neural_signature):
    global _model
    if _model is None:
        _model = SwarmGNN()
        _model.load_state_dict(torch.load("swarm_gnn.pt"))
        _model.eval()

    # Build graph
    positions = torch.tensor([[a.x, a.y, a.z] for a in agents])
    velocities = torch.tensor([[a.vx, a.vy, a.vz] for a in agents])
    sig = torch.tensor([list(neural_signature.values())])  # (1, 6)
    sig_expanded = sig.expand(len(agents), -1)             # (N, 6)

    node_features = torch.cat([positions, velocities, sig_expanded, ...], dim=-1)
    edge_index = radius_graph(positions, r=8.0)

    data = Data(x=node_features, edge_index=edge_index)
    with torch.no_grad():
        output = _model(data)

    # output[:, :3] = new velocity, output[:, 3:6] = position delta, etc.
    # Convert back to AgentState list
    ...
```

---

## Async Safety

Both mock functions are synchronous. When replaced with GPU-bound inference:

```python
# In simulation/engine.py — wrap the blocking call:
import asyncio

loop = asyncio.get_event_loop()
self.agents = await loop.run_in_executor(
    None,  # default thread pool executor
    mock_advance_swarm,
    self.agents,
    self.neural_signature,
)
```

For the neural signature (called once per simulation start in `main.py`):

```python
neural_signature = await asyncio.get_event_loop().run_in_executor(
    None, mock_get_neural_signature, request.media_url
)
```

## GPU Memory Management

- **Model loading**: Use lazy initialization (`_model = None` pattern shown above) to avoid loading models until first use.
- **Batch inference**: If running multiple simulations, batch their swarm tensors before the forward pass to maximize GPU utilization.
- **Memory cleanup**: Call `torch.cuda.empty_cache()` after large simulations end.
- **Mixed precision**: Use `torch.cuda.amp.autocast()` for 2x inference speedup with minimal accuracy loss.

## Testing with Real Models

1. Install the ML dependencies: `pip install -e ".[ml]"`
2. Place model weights in `backend/weights/` (gitignored)
3. Set environment variable `USE_REAL_MODELS=1` to switch from mock to real
4. Run the same test suite — the function signatures are identical
