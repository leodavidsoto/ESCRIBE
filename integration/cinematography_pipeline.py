"""
Integration module for cinematography pipeline.

Provides functions to apply color grading, effects, and transitions
from director_flow specifications to video clips.
"""
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("cinematography_pipeline")


def _get_cinematography_engines():
    """Lazy load cinematography engines."""
    try:
        from cinematography.color_grading_engine import ColorGradingEngine
        from cinematography.effects_engine import EffectsEngine
        from cinematography.transition_engine import TransitionEngine
        return ColorGradingEngine(), EffectsEngine(), TransitionEngine()
    except ImportError:
        log.warning("cinematography_engines_not_available")
        return None, None, None


def apply_cinematography_to_scene(
    video_path: Path,
    scene: dict,
    output_path: Path,
) -> bool:
    """Apply color grading and effects from scene cinematography specs.

    Args:
        video_path: Input video file path
        scene: Scene dictionary with master_stack.cinematography
        output_path: Output video file path

    Returns:
        True if applied successfully, False otherwise
    """
    color_grading_engine, effects_engine, _ = _get_cinematography_engines()
    if not color_grading_engine or not effects_engine:
        log.warning("cinematography_not_available")
        return False

    try:
        master_stack = scene.get("master_stack", {})
        cinematography = master_stack.get("cinematography", {})

        if not cinematography:
            log.debug("no_cinematography_specs_for_scene", extra={"scene_id": scene.get("id")})
            return False

        # Extract color grading specs
        color_grading = cinematography.get("color_grading", {})
        profile = color_grading.get("profile", "cinematic_default")
        intensity = float(color_grading.get("intensity", 1.0))

        # Extract effects specs
        effects_list = cinematography.get("effects", [])

        # Build FFmpeg command base
        cmd = ["ffmpeg", "-i", str(video_path), "-c:v", "libx264", "-preset", "medium"]

        # Apply color grading filter
        if profile:
            is_valid, error = color_grading_engine.validate_profile(profile)
            if is_valid:
                filter_chain = color_grading_engine.get_filter_chain(profile, intensity)
                if filter_chain:
                    cmd = color_grading_engine.apply_to_command(cmd, profile, intensity)
                    log.info("color_grading_applied", extra={"profile": profile, "intensity": intensity})
            else:
                log.warning("invalid_color_grading_profile", extra={"profile": profile, "error": error})

        # Apply effects chain
        if effects_list:
            cmd = effects_engine.apply_to_command(cmd, effects_list)
            log.info("effects_applied", extra={"effect_count": len(effects_list)})

        # Add output path
        cmd.extend(["-y", str(output_path)])

        # Execute FFmpeg
        import subprocess
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            log.info("cinematography_applied_successfully", extra={"output": str(output_path)})
            return True
        else:
            log.error("ffmpeg_execution_failed", extra={"stderr": result.stderr[:200]})
            return False

    except Exception as e:
        log.error("cinematography_application_error", extra={"error": str(e)})
        return False


def apply_transition(
    from_clip: Path,
    to_clip: Path,
    output_path: Path,
    transition_spec: dict = None,
) -> bool:
    """Apply transition between two video clips.

    Args:
        from_clip: First video clip
        to_clip: Second video clip
        output_path: Output video path
        transition_spec: Transition specification dict with type and duration

    Returns:
        True if successful, False otherwise
    """
    _, _, transition_engine = _get_cinematography_engines()
    if not transition_engine:
        log.warning("transition_engine_not_available")
        return False

    try:
        if not transition_spec:
            transition_spec = {"type": "crossfade", "duration": 1.0}

        transition_type = transition_spec.get("type", "crossfade")
        duration = float(transition_spec.get("duration", 1.0))

        # Validate transition
        is_valid, error = transition_engine.validate_transition(transition_type)
        if not is_valid:
            log.warning("invalid_transition_type", extra={"type": transition_type, "error": error})
            return False

        # Build FFmpeg command for concatenation with transition
        cmd = [
            "ffmpeg",
            "-i", str(from_clip),
            "-i", str(to_clip),
        ]

        filter_str = transition_engine.get_filter(transition_type, duration)
        if filter_str:
            cmd.extend(["-filter_complex", filter_str, "-c:v", "libx264", "-preset", "medium", "-y", str(output_path)])

            import subprocess
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                log.info("transition_applied", extra={"type": transition_type, "duration": duration})
                return True
            else:
                log.error("ffmpeg_transition_failed", extra={"stderr": result.stderr[:200]})
                return False
        else:
            log.warning("failed_to_generate_transition_filter", extra={"type": transition_type})
            return False

    except Exception as e:
        log.error("transition_application_error", extra={"error": str(e)})
        return False


def build_ffmpeg_filter_chain_from_director_flow(director_flow: dict) -> str:
    """Build complete FFmpeg filter chain from director flow specs.

    Args:
        director_flow: Complete director flow with scenes and cinematography

    Returns:
        FFmpeg filter chain string
    """
    color_grading_engine, effects_engine, _ = _get_cinematography_engines()
    if not color_grading_engine or not effects_engine:
        return ""

    filter_parts = []

    try:
        scenes = director_flow.get("scenes", [])
        for scene in scenes:
            master_stack = scene.get("master_stack", {})
            cinematography = master_stack.get("cinematography", {})

            if not cinematography:
                continue

            # Add color grading
            color_grading = cinematography.get("color_grading", {})
            if color_grading:
                profile = color_grading.get("profile", "cinematic_default")
                intensity = float(color_grading.get("intensity", 1.0))
                filter_str = color_grading_engine.get_filter_chain(profile, intensity)
                if filter_str:
                    filter_parts.append(filter_str)

            # Add effects
            effects_list = cinematography.get("effects", [])
            if effects_list:
                effects_chain = effects_engine.chain_effects(effects_list)
                if effects_chain:
                    filter_parts.append(effects_chain)

        # Join all filters with comma separator
        return ",".join(filter_parts)

    except Exception as e:
        log.error("filter_chain_generation_error", extra={"error": str(e)})
        return ""
