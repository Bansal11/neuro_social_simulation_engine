"""
Mock swarm physics engine using boid-style rules weighted by neural signature.

# MOCK: Replace mock_advance_swarm with a real JAX / PyTorch GNN swarm model.
#
# Integration contract:
#   Input:  agents: list[AgentState]       — current swarm state
#           neural_signature: dict[str, float]  — fMRI activations from mock_neural.py
#   Output: list[AgentState]               — updated swarm state (same length, same IDs)
#
# Async safety: this function is synchronous numpy.  If replaced with a GPU
# model, wrap the call:
#   loop = asyncio.get_event_loop()
#   agents = await loop.run_in_executor(None, real_advance_swarm, agents, sig)
"""
from __future__ import annotations

import numpy as np

from models import AgentState, AgentStateEnum

# ---------------------------------------------------------------------------
# Tunable constants (exposed for test assertions)
# ---------------------------------------------------------------------------

#: Base maximum speed.  Scaled per-tick by amygdala_arousal.
MAX_SPEED: float = 3.0

#: Neighbourhood radii for each boid rule.
SEP_RADIUS: float = 2.0
ALI_RADIUS: float = 5.0
COH_RADIUS: float = 8.0

#: Influence score threshold above which an agent becomes EXCITED.
EXCITE_THRESHOLD: float = 0.7

#: Consecutive ticks an agent stays EXCITED before exhaustion.
EXHAUSTION_TICKS: int = 30

# ---------------------------------------------------------------------------
# Module-level state (persists across ticks within one process)
# ---------------------------------------------------------------------------

# Maps agent_id → number of consecutive ticks spent in the EXCITED state.
_excited_tick_counts: dict[int, int] = {}


def mock_advance_swarm(
    agents: list[AgentState],
    neural_signature: dict[str, float],
) -> list[AgentState]:
    """
    Advance the swarm by one tick using boid physics weighted by *neural_signature*.

    Boid rules and their neural correlates:
    - **Separation**  (radius 2.0)  — weighted by ``anterior_insula_valence``
      (high valence → greater personal-space preference)
    - **Alignment**   (radius 5.0)  — weighted by ``posterior_superior_temporal_sulcus_social``
      (social-cognition region drives velocity matching)
    - **Cohesion**    (radius 8.0)  — weighted by ``nucleus_accumbens_motivation``
      (motivational drive pulls agents toward local centre of mass)
    - **Reward drift**              — ``ventral_striatum_reward`` attracts agents toward origin
    - **Arousal noise**             — ``amygdala_arousal`` adds random velocity perturbation

    State machine transitions (evaluated after physics):
    - EXCITED      if influence_score > EXCITE_THRESHOLD
    - PROPAGATING  if any neighbour is EXCITED and motivation > 0.6
    - INHIBITED    if regulation > 0.8 (overrides other transitions)
    - EXHAUSTED    if EXCITED for > EXHAUSTION_TICKS consecutive ticks
    - NEUTRAL      otherwise

    Args:
        agents: Current list of AgentState objects.
        neural_signature: Dict of 6 fMRI activation scores in [0, 1].

    Returns:
        Updated list of AgentState objects (same length and agent IDs).
    """
    n = len(agents)
    if n == 0:
        return agents

    # -- Unpack neural signature weights ------------------------------------
    reward      = neural_signature.get("ventral_striatum_reward", 0.5)
    valence     = neural_signature.get("anterior_insula_valence", 0.5)
    arousal     = neural_signature.get("amygdala_arousal", 0.5)
    regulation  = neural_signature.get("prefrontal_cortex_regulation", 0.5)
    motivation  = neural_signature.get("nucleus_accumbens_motivation", 0.5)
    social      = neural_signature.get("posterior_superior_temporal_sulcus_social", 0.5)

    # -- Build numpy arrays -------------------------------------------------
    pos = np.array([[a.x, a.y, a.z] for a in agents], dtype=np.float32)    # (N, 3)
    vel = np.array([[a.vx, a.vy, a.vz] for a in agents], dtype=np.float32) # (N, 3)
    states = [a.state for a in agents]

    # -- Compute pairwise distances (N × N) ---------------------------------
    diff = pos[:, np.newaxis, :] - pos[np.newaxis, :, :]  # (N, N, 3)
    dist = np.linalg.norm(diff, axis=-1)                   # (N, N)
    np.fill_diagonal(dist, np.inf)                         # exclude self

    # -- Boid rules ---------------------------------------------------------
    sep_mask = (dist < SEP_RADIUS)                         # (N, N) bool
    ali_mask = (dist < ALI_RADIUS)
    coh_mask = (dist < COH_RADIUS)

    accel = np.zeros_like(vel)

    # Separation: steer away from too-close neighbours
    sep_counts = sep_mask.sum(axis=1, keepdims=True).clip(min=1)
    sep_vec = -(diff * sep_mask[:, :, np.newaxis]).sum(axis=1) / sep_counts
    accel += sep_vec * (valence * 0.8)

    # Alignment: match velocity of nearby agents
    ali_counts = ali_mask.sum(axis=1, keepdims=True).clip(min=1)
    ali_vel = (vel[np.newaxis, :, :] * ali_mask[:, :, np.newaxis]).sum(axis=1) / ali_counts
    accel += (ali_vel - vel) * (social * 0.5)

    # Cohesion: steer toward local centre of mass
    coh_counts = coh_mask.sum(axis=1, keepdims=True).clip(min=1)
    coh_center = (pos[np.newaxis, :, :] * coh_mask[:, :, np.newaxis]).sum(axis=1) / coh_counts
    accel += (coh_center - pos) * (motivation * 0.3)

    # Reward drift: weak attractor toward origin
    accel += (-pos) * (reward * 0.05)

    # Arousal noise: random perturbation
    noise = np.random.default_rng().standard_normal((n, 3)).astype(np.float32)
    accel += noise * (arousal * 0.08)

    # -- Integrate ----------------------------------------------------------
    vel = vel + accel
    effective_max_speed = max(0.05, MAX_SPEED * max(0.1, arousal))
    speeds = np.linalg.norm(vel, axis=-1, keepdims=True)
    too_fast = speeds > effective_max_speed
    vel = np.where(too_fast, vel / speeds * effective_max_speed, vel)
    pos = pos + vel

    # -- Influence score: fraction of EXCITED neighbours in coh radius ------
    is_excited = np.array(
        [s == AgentStateEnum.EXCITED or s == "EXCITED" for s in states], dtype=np.float32
    )
    excited_neighbours = (is_excited[np.newaxis, :] * coh_mask).sum(axis=1)
    total_neighbours = coh_mask.sum(axis=1).clip(min=1)
    influence = np.clip(excited_neighbours / total_neighbours, 0.0, 1.0)

    # -- State machine transitions ------------------------------------------
    new_agents: list[AgentState] = []
    for i, agent in enumerate(agents):
        score = float(influence[i])

        # Determine new state
        if regulation > 0.8:
            new_state = AgentStateEnum.INHIBITED
        elif score > EXCITE_THRESHOLD:
            tick_count = _excited_tick_counts.get(agent.id, 0) + 1
            _excited_tick_counts[agent.id] = tick_count
            if tick_count > EXHAUSTION_TICKS:
                new_state = AgentStateEnum.EXHAUSTED
                _excited_tick_counts[agent.id] = 0
            else:
                new_state = AgentStateEnum.EXCITED
        elif (
            is_excited[i] or states[i] == AgentStateEnum.PROPAGATING
        ) and motivation > 0.6 and (coh_mask[i] & (is_excited > 0)).any():
            new_state = AgentStateEnum.PROPAGATING
            _excited_tick_counts.pop(agent.id, None)
        else:
            new_state = AgentStateEnum.NEUTRAL
            _excited_tick_counts.pop(agent.id, None)

        new_agents.append(
            AgentState(
                id=agent.id,
                x=float(pos[i, 0]),
                y=float(pos[i, 1]),
                z=float(pos[i, 2]),
                vx=float(vel[i, 0]),
                vy=float(vel[i, 1]),
                vz=float(vel[i, 2]),
                state=new_state,
                influence_score=score,
            )
        )

    return new_agents
