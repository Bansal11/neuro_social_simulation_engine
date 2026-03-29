"""
Tests for backend/simulation/mock_neural.py.
Written before implementation (TDD).
"""

EXPECTED_KEYS = {
    "ventral_striatum_reward",
    "anterior_insula_valence",
    "amygdala_arousal",
    "prefrontal_cortex_regulation",
    "nucleus_accumbens_motivation",
    "posterior_superior_temporal_sulcus_social",
}


def test_returns_all_six_keys():
    """Output dict must contain exactly the 6 fMRI region keys."""
    from simulation.mock_neural import mock_get_neural_signature

    result = mock_get_neural_signature("https://example.com/video")
    assert set(result.keys()) == EXPECTED_KEYS


def test_values_in_unit_range():
    """All activation scores must lie in [0.0, 1.0]."""
    from simulation.mock_neural import mock_get_neural_signature

    result = mock_get_neural_signature("https://example.com/video")
    for key, value in result.items():
        assert 0.0 <= value <= 1.0, f"{key}={value} is outside [0, 1]"


def test_deterministic_for_same_url():
    """Calling with the same URL twice must return identical signatures."""
    from simulation.mock_neural import mock_get_neural_signature

    url = "https://example.com/travel-video"
    first = mock_get_neural_signature(url)
    second = mock_get_neural_signature(url)
    assert first == second


def test_different_urls_produce_different_signatures():
    """Different URLs should produce different neural signatures."""
    from simulation.mock_neural import mock_get_neural_signature

    sig_a = mock_get_neural_signature("https://example.com/video-a")
    sig_b = mock_get_neural_signature("https://example.com/video-b")
    assert sig_a != sig_b


def test_accepts_arbitrary_url_string():
    """Function must not crash on edge-case URL strings."""
    from simulation.mock_neural import mock_get_neural_signature

    for url in ["", "not-a-url", "ftp://weird/path?q=1", "x" * 1000]:
        result = mock_get_neural_signature(url)
        assert isinstance(result, dict)
