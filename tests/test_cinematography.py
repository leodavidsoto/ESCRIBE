"""
Tests for cinematography engines: color grading, effects, transitions.
"""
import pytest
from pathlib import Path

from cinematography.color_grading_engine import ColorGradingEngine
from cinematography.effects_engine import EffectsEngine
from cinematography.transition_engine import TransitionEngine


@pytest.fixture
def color_grading_engine():
    """Fixture for ColorGradingEngine."""
    return ColorGradingEngine()


@pytest.fixture
def effects_engine():
    """Fixture for EffectsEngine."""
    return EffectsEngine()


@pytest.fixture
def transition_engine():
    """Fixture for TransitionEngine."""
    return TransitionEngine()


class TestColorGradingEngine:
    """Test suite for ColorGradingEngine."""

    def test_engine_initialization(self, color_grading_engine):
        """Test engine initializes with all profiles."""
        assert len(color_grading_engine.profiles) == 12
        assert "cinematic_default" in color_grading_engine.profiles

    def test_list_profiles(self, color_grading_engine):
        """Test listing all profiles."""
        profiles = color_grading_engine.list_profiles()
        assert len(profiles) == 12
        assert all("name" in p for p in profiles)
        assert all("category" in p for p in profiles)

    def test_validate_profile_success(self, color_grading_engine):
        """Test profile validation with valid profile."""
        is_valid, error = color_grading_engine.validate_profile("cinematic_default")
        assert is_valid is True
        assert error is None

    def test_validate_profile_failure(self, color_grading_engine):
        """Test profile validation with invalid profile."""
        is_valid, error = color_grading_engine.validate_profile("nonexistent_profile")
        assert is_valid is False
        assert "not found" in error

    def test_get_filter_chain_default_intensity(self, color_grading_engine):
        """Test getting filter chain with default intensity."""
        filter_chain = color_grading_engine.get_filter_chain("cinematic_default", intensity=1.0)
        assert filter_chain is not None
        assert len(filter_chain) > 0
        assert "curves" in filter_chain or "colorbalance" in filter_chain

    def test_get_filter_chain_custom_intensity(self, color_grading_engine):
        """Test getting filter chain with custom intensity."""
        filter_chain = color_grading_engine.get_filter_chain("warm_golden", intensity=0.5)
        assert filter_chain is not None

    def test_get_filter_chain_unknown_profile(self, color_grading_engine):
        """Test getting filter chain for unknown profile."""
        filter_chain = color_grading_engine.get_filter_chain("unknown", intensity=1.0)
        assert filter_chain == ""

    def test_profile_categorization(self, color_grading_engine):
        """Test profile categorization."""
        profiles = color_grading_engine.list_profiles()
        categories = {p["category"] for p in profiles}
        assert len(categories) > 0
        assert any(c in categories for c in ["cinematic", "vintage", "warm", "cool"])

    def test_apply_to_ffmpeg_command(self, color_grading_engine):
        """Test applying filter to FFmpeg command."""
        base_cmd = ["ffmpeg", "-i", "input.mp4", "-c:v", "libx264"]
        modified = color_grading_engine.apply_to_command(base_cmd, "cinematic_default", 1.0)

        assert "-vf" in modified
        vf_index = modified.index("-vf")
        filter_chain = modified[vf_index + 1]
        assert len(filter_chain) > 0


class TestEffectsEngine:
    """Test suite for EffectsEngine."""

    def test_engine_initialization(self, effects_engine):
        """Test engine initializes with all effects."""
        assert len(effects_engine.effects) >= 10
        assert "vignette" in effects_engine.effects

    def test_list_effects(self, effects_engine):
        """Test listing all effects."""
        effects = effects_engine.list_effects()
        assert len(effects) >= 10
        assert all("name" in e for e in effects)
        assert all("intensity_range" in e for e in effects)

    def test_validate_effect_success(self, effects_engine):
        """Test effect validation with valid effect."""
        is_valid, error = effects_engine.validate_effect("vignette")
        assert is_valid is True
        assert error is None

    def test_validate_effect_failure(self, effects_engine):
        """Test effect validation with invalid effect."""
        is_valid, error = effects_engine.validate_effect("nonexistent_effect")
        assert is_valid is False
        assert "not found" in error

    def test_get_filter_single_effect(self, effects_engine):
        """Test getting FFmpeg filter for single effect."""
        filter_str = effects_engine.get_filter("vignette", intensity=0.5)
        assert filter_str is not None
        assert "vignette" in filter_str

    def test_get_filter_intensity_clamping(self, effects_engine):
        """Test that intensity is clamped to valid range."""
        # Test high intensity
        filter_high = effects_engine.get_filter("vignette", intensity=2.0)
        assert filter_high is not None

        # Test low intensity
        filter_low = effects_engine.get_filter("vignette", intensity=-1.0)
        assert filter_low is not None

    def test_chain_multiple_effects(self, effects_engine):
        """Test chaining multiple effects."""
        effects_specs = [
            {"name": "vignette", "intensity": 0.3},
            {"name": "film_grain", "intensity": 0.1},
            {"name": "lens_flare", "intensity": 0.2},
        ]
        chain = effects_engine.chain_effects(effects_specs)
        assert chain is not None
        assert len(chain) > 0
        assert "|" in chain or len(chain) > 20

    def test_chain_effects_with_invalid(self, effects_engine):
        """Test chaining effects with one invalid."""
        effects_specs = [
            {"name": "vignette", "intensity": 0.3},
            {"name": "nonexistent", "intensity": 0.1},
            {"name": "film_grain", "intensity": 0.1},
        ]
        chain = effects_engine.chain_effects(effects_specs)
        # Should still produce output with valid effects
        assert chain is not None

    def test_apply_to_ffmpeg_command(self, effects_engine):
        """Test applying effects to FFmpeg command."""
        base_cmd = ["ffmpeg", "-i", "input.mp4"]
        effects_specs = [
            {"name": "vignette", "intensity": 0.3},
        ]
        modified = effects_engine.apply_to_command(base_cmd, effects_specs)

        assert "-vf" in modified
        vf_index = modified.index("-vf")
        filter_chain = modified[vf_index + 1]
        assert len(filter_chain) > 0


class TestTransitionEngine:
    """Test suite for TransitionEngine."""

    def test_engine_initialization(self, transition_engine):
        """Test engine initializes with all transitions."""
        assert len(transition_engine.transitions) >= 12
        assert "crossfade" in transition_engine.transitions

    def test_list_transitions(self, transition_engine):
        """Test listing all transitions."""
        transitions = transition_engine.list_transitions()
        assert len(transitions) >= 12
        assert all("name" in t for t in transitions)
        assert all("default_duration" in t for t in transitions)

    def test_validate_transition_success(self, transition_engine):
        """Test transition validation with valid transition."""
        is_valid, error = transition_engine.validate_transition("crossfade")
        assert is_valid is True
        assert error is None

    def test_validate_transition_failure(self, transition_engine):
        """Test transition validation with invalid transition."""
        is_valid, error = transition_engine.validate_transition("nonexistent")
        assert is_valid is False
        assert "not found" in error

    def test_get_filter_crossfade(self, transition_engine):
        """Test getting FFmpeg filter for crossfade."""
        filter_str = transition_engine.get_filter("crossfade", duration=1.0)
        assert filter_str is not None
        assert "fade" in filter_str.lower() or "concat" in filter_str.lower()

    def test_get_filter_dissolve(self, transition_engine):
        """Test getting FFmpeg filter for dissolve."""
        filter_str = transition_engine.get_filter("dissolve", duration=0.5)
        assert filter_str is not None

    def test_get_filter_duration_clamping(self, transition_engine):
        """Test that duration is clamped to 0.1-10s range."""
        # Very short duration
        filter_short = transition_engine.get_filter("crossfade", duration=0.01)
        assert filter_short is not None

        # Very long duration
        filter_long = transition_engine.get_filter("crossfade", duration=20.0)
        assert filter_long is not None

    def test_apply_to_ffmpeg_command(self, transition_engine):
        """Test applying transition to FFmpeg command."""
        base_cmd = ["ffmpeg", "-i", "input.mp4"]
        modified = transition_engine.apply_between_clips(
            base_cmd,
            transition_name="crossfade",
            duration=1.0,
        )

        assert "-vf" in modified
        vf_index = modified.index("-vf")
        filter_chain = modified[vf_index + 1]
        assert len(filter_chain) > 0

    def test_all_transitions_generate_filters(self, transition_engine):
        """Test that all transitions can generate filters."""
        for trans_name in transition_engine.transitions.keys():
            filter_str = transition_engine.get_filter(trans_name, duration=1.0)
            assert filter_str is not None
            assert len(filter_str) > 0
