"""
Transition engine for inter-scene video transitions.

Supports crossfade, dissolve, wipe, slide, and custom transition effects.
"""
import logging
from dataclasses import dataclass
from typing import Literal, Optional

log = logging.getLogger("transition_engine")


@dataclass
class TransitionDefinition:
    """Transition definition with FFmpeg filter."""
    name: str
    description: str
    ffmpeg_filter_template: str  # Template with {duration} placeholder
    default_duration: float = 1.0  # seconds


# Predefined transitions catalog
TRANSITIONS_CATALOG = {
    "crossfade": TransitionDefinition(
        name="Crossfade",
        description="Simple crossfade between clips",
        ffmpeg_filter_template="concat=n=2:v=1:a=0,fade=t=out:st=0:d={duration}",
        default_duration=1.0,
    ),
    "dissolve": TransitionDefinition(
        name="Dissolve",
        description="Smooth dissolve transition",
        ffmpeg_filter_template="xfade=transition=dissolve:duration={duration}",
        default_duration=0.5,
    ),
    "fade_black": TransitionDefinition(
        name="Fade to Black",
        description="Fade out to black and fade in",
        ffmpeg_filter_template="fade=t=out:st=0:d={duration},fade=t=in:st={duration}:d={duration}",
        default_duration=1.0,
    ),
    "fade_white": TransitionDefinition(
        name="Fade to White",
        description="Fade out to white and fade in",
        ffmpeg_filter_template="colorchannelmixer=1:1:1,fade=t=out:st=0:d={duration},colorchannelmixer=0:0:0,fade=t=in:st={duration}:d={duration}",
        default_duration=1.0,
    ),
    "slide_left": TransitionDefinition(
        name="Slide Left",
        description="Second clip slides in from right",
        ffmpeg_filter_template="xfade=transition=slideright:duration={duration}",
        default_duration=1.0,
    ),
    "slide_right": TransitionDefinition(
        name="Slide Right",
        description="Second clip slides in from left",
        ffmpeg_filter_template="xfade=transition=slideleft:duration={duration}",
        default_duration=1.0,
    ),
    "slide_up": TransitionDefinition(
        name="Slide Up",
        description="Second clip slides in from bottom",
        ffmpeg_filter_template="xfade=transition=slidedown:duration={duration}",
        default_duration=1.0,
    ),
    "slide_down": TransitionDefinition(
        name="Slide Down",
        description="Second clip slides in from top",
        ffmpeg_filter_template="xfade=transition=slideup:duration={duration}",
        default_duration=1.0,
    ),
    "wipe_right": TransitionDefinition(
        name="Wipe Right",
        description="Right-to-left wipe transition",
        ffmpeg_filter_template="xfade=transition=wiperight:duration={duration}",
        default_duration=1.0,
    ),
    "wipe_left": TransitionDefinition(
        name="Wipe Left",
        description="Left-to-right wipe transition",
        ffmpeg_filter_template="xfade=transition=wipeleft:duration={duration}",
        default_duration=1.0,
    ),
    "zoom_in": TransitionDefinition(
        name="Zoom In",
        description="Zoom transition between clips",
        ffmpeg_filter_template="xfade=transition=zoomin:duration={duration}",
        default_duration=1.0,
    ),
    "blur_transition": TransitionDefinition(
        name="Blur Transition",
        description="Blur effect transition",
        ffmpeg_filter_template="xfade=transition=blur:duration={duration}",
        default_duration=1.0,
    ),
}


class TransitionEngine:
    """Manages video transitions between scenes."""

    def __init__(self):
        """Initialize transition engine."""
        self.transitions = TRANSITIONS_CATALOG
        log.info("transition_engine_ready", extra={"transitions": len(self.transitions)})

    def get_filter(
        self,
        transition_name: str,
        duration: float = 1.0,
    ) -> Optional[str]:
        """Get FFmpeg filter for a transition.

        Args:
            transition_name: Transition name key
            duration: Transition duration in seconds

        Returns:
            FFmpeg filter string or None if transition not found
        """
        if transition_name not in self.transitions:
            log.warning(f"Unknown transition: {transition_name}")
            return None

        transition = self.transitions[transition_name]
        # Clamp duration to 0.1 - 10 seconds
        clamped_duration = max(0.1, min(10.0, duration))

        try:
            filter_str = transition.ffmpeg_filter_template.format(duration=clamped_duration)
            return filter_str
        except (KeyError, ValueError) as e:
            log.error(f"transition_format_error: {e}")
            return None

    def list_transitions(self) -> list[dict]:
        """List all available transitions."""
        return [
            {
                "name": name,
                "description": transition.description,
                "default_duration": transition.default_duration,
            }
            for name, transition in self.transitions.items()
        ]

    def validate_transition(self, transition_name: str) -> tuple[bool, Optional[str]]:
        """Validate that a transition exists.

        Args:
            transition_name: Transition name to validate

        Returns:
            (is_valid, error_message)
        """
        if transition_name in self.transitions:
            return True, None
        return False, f"Transition '{transition_name}' not found"

    def apply_between_clips(
        self,
        ffmpeg_cmd: list[str],
        transition_name: str = "crossfade",
        duration: float = 1.0,
    ) -> list[str]:
        """Insert transition filter into FFmpeg command.

        Args:
            ffmpeg_cmd: Base FFmpeg command array
            transition_name: Transition to apply
            duration: Duration in seconds

        Returns:
            Modified FFmpeg command with transition inserted
        """
        filter_str = self.get_filter(transition_name, duration)
        if not filter_str:
            return ffmpeg_cmd

        try:
            vf_index = ffmpeg_cmd.index("-vf")
            ffmpeg_cmd[vf_index + 1] += f",{filter_str}"
        except ValueError:
            ffmpeg_cmd.extend(["-vf", filter_str])

        log.info("transition_applied", extra={"transition": transition_name, "duration": duration})
        return ffmpeg_cmd
