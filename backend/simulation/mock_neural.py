"""
Mock neural signature extractor.

# MOCK: Replace this entire function body with real TRIBE v2 fMRI inference.
#
# Integration contract:
#   Input:  media_url: str  — URL pointing to a video, audio, or image file
#   Output: dict[str, float] — predicted fMRI activation scores, all in [0.0, 1.0]
#   Keys must match NEURAL_REGIONS exactly (the swarm physics depends on them).
#
# Async safety: if the real model is GPU-bound (blocking), wrap the call in
#   asyncio.get_event_loop().run_in_executor(None, mock_get_neural_signature, url)
# to avoid blocking the FastAPI event loop.
"""
from __future__ import annotations

import hashlib

import numpy as np

# The six fMRI regions whose activations drive swarm behaviour.
# Order matters: the numpy RNG draws values in this sequence.
NEURAL_REGIONS: tuple[str, ...] = (
    "ventral_striatum_reward",
    "anterior_insula_valence",
    "amygdala_arousal",
    "prefrontal_cortex_regulation",
    "nucleus_accumbens_motivation",
    "posterior_superior_temporal_sulcus_social",
)


def mock_get_neural_signature(media_url: str) -> dict[str, float]:
    """
    Return a deterministic mock neural signature for *media_url*.

    The same URL always produces the same signature, enabling reproducible
    simulation replays during development and testing.

    Args:
        media_url: Arbitrary string (URL) identifying the media to analyse.

    Returns:
        Dictionary mapping each of the six fMRI region names to a predicted
        activation score in the range [0.0, 1.0].
    """
    # Derive a deterministic integer seed from the URL string.
    # MD5 is used here purely for speed and determinism — not for security.
    digest = hashlib.md5(media_url.encode("utf-8", errors="replace")).digest()
    seed = int.from_bytes(digest, byteorder="big")

    rng = np.random.default_rng(seed)
    activations = rng.uniform(0.0, 1.0, size=len(NEURAL_REGIONS))

    return dict(zip(NEURAL_REGIONS, activations.tolist()))
