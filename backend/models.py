"""
Pydantic v2 data models for the Neuro-Social Simulation Engine.

All request/response and WebSocket payload schemas are defined here and
imported by other modules. No business logic lives in this file.
"""
from __future__ import annotations

import enum
import time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Agent state machine
# ---------------------------------------------------------------------------

class AgentStateEnum(str, enum.Enum):
    """
    Discrete biological states for each MiroFish agent.

    States are inspired by neural activation dynamics:
    - NEUTRAL:     baseline low-activation resting state
    - EXCITED:     high dopaminergic / reward-driven activity
    - INHIBITED:   prefrontal down-regulation of excitation
    - PROPAGATING: spreading activation to neighbouring agents
    - EXHAUSTED:   post-excitation refractory period
    """

    NEUTRAL = "NEUTRAL"
    EXCITED = "EXCITED"
    INHIBITED = "INHIBITED"
    PROPAGATING = "PROPAGATING"
    EXHAUSTED = "EXHAUSTED"


# ---------------------------------------------------------------------------
# Core agent representation
# ---------------------------------------------------------------------------

class AgentState(BaseModel):
    """
    Full kinematic and biological state of a single swarm agent at one tick.

    Positions and velocities are in arbitrary simulation units.
    influence_score ∈ [0, 1] quantifies how strongly this agent is currently
    influencing its local neighbourhood.
    """

    model_config = ConfigDict(use_enum_values=True)

    id: int = Field(..., description="Unique agent identifier within a simulation")
    x: float = Field(..., description="Position — x axis")
    y: float = Field(..., description="Position — y axis")
    z: float = Field(..., description="Position — z axis")
    vx: float = Field(..., description="Velocity — x component")
    vy: float = Field(..., description="Velocity — y component")
    vz: float = Field(..., description="Velocity — z component")
    state: AgentStateEnum = Field(..., description="Current biological state")
    influence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalised influence on neighbouring agents [0, 1]",
    )


# ---------------------------------------------------------------------------
# REST API schemas
# ---------------------------------------------------------------------------

class SimulationRequest(BaseModel):
    """
    Body for POST /api/v1/simulate.

    media_url is passed to the neural signature extractor (TRIBE v2 or mock).
    swarm_size controls how many MiroFish agents are spawned.
    """

    media_url: str = Field(..., description="URL of the media to analyse (video, audio, image)")
    swarm_size: int = Field(
        default=500,
        ge=1,
        le=5000,
        description="Number of swarm agents to spawn [1, 5000]",
    )


class SimulationResponse(BaseModel):
    """
    Response body for POST /api/v1/simulate.

    Returns the assigned simulation_id (used to open the WebSocket) and the
    neural signature that was extracted from the media URL.
    """

    simulation_id: str = Field(..., description="UUID identifying this simulation run")
    swarm_size: int = Field(..., description="Number of agents spawned")
    neural_signature: dict[str, float] = Field(
        ...,
        description="Predicted fMRI activations extracted from the media [0, 1] per region",
    )


# ---------------------------------------------------------------------------
# WebSocket payload schema
# ---------------------------------------------------------------------------

class SimulationTick(BaseModel):
    """
    One simulation tick broadcast over the WebSocket.

    Sent to all connected clients at ~10 FPS by the SimulationEngine.
    The 'agents' list contains the full state of every agent at this tick.
    """

    model_config = ConfigDict(use_enum_values=True)

    tick: int = Field(..., description="Monotonically increasing tick counter (starts at 1)")
    simulation_id: str = Field(..., description="UUID of the parent simulation")
    timestamp: float = Field(
        default_factory=time.time,
        description="Unix epoch timestamp when this tick was generated (server time)",
    )
    agents: list[AgentState] = Field(..., description="Full swarm state at this tick")
