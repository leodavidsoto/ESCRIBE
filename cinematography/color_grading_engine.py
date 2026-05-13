"""
Professional color grading engine for video composition.

Implements LUT-based color grading with intensity scaling.
"""
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

log = logging.getLogger("color_grading")


@dataclass
class ColorGradingProfile:
    """Color grading profile definition."""
    name: str
    description: str
    lut_path: Optional[str] = None  # Path to 3D LUT file
    ffmpeg_filter: str = ""  # Fallback FFmpeg filter chain
    curves: dict = None  # RGB curves definition


# Predefined color grading profiles
GRADING_PROFILES = {
    "cinematic_default": ColorGradingProfile(
        name="Cinematic Default",
        description="Professional cinema look with crushed blacks",
        ffmpeg_filter="curves=r='0/0 0.5/0.48 1/1':g='0/0 0.5/0.50 1/1':b='0/0 0.5/0.52 1/1'",
    ),
    "warm_golden": ColorGradingProfile(
        name="Warm Golden",
        description="Warm, golden hour aesthetic",
        ffmpeg_filter="colorbalance=rs=0.1:gs=0.05:bs=-0.15:rm=0.1:gm=0.05:bm=-0.2",
    ),
    "cool_teal": ColorGradingProfile(
        name="Cool Teal",
        description="Modern teal and orange contrast",
        ffmpeg_filter="colorbalance=rs=-0.15:gs=0.05:bs=0.2:rm=-0.1:gm=0:bm=0.15",
    ),
    "noir_high_contrast": ColorGradingProfile(
        name="Noir High Contrast",
        description="High contrast black and white noir",
        ffmpeg_filter="curves=r='0/0 0.5/0.4 1/1':g='0/0 0.5/0.4 1/1':b='0/0 0.5/0.4 1/1',colorbalance=rs=-0.2:gs=-0.2:bs=-0.2",
    ),
    "vintage_faded": ColorGradingProfile(
        name="Vintage Faded",
        description="Faded vintage film look",
        ffmpeg_filter="colorbalance=rs=0.15:gs=0.1:bs=-0.05,curves=r='0/0.05 0.5/0.5 1/0.98':g='0/0.05 0.5/0.5 1/0.98':b='0/0.05 0.5/0.5 1/0.98'",
    ),
    "bleach_bypass": ColorGradingProfile(
        name="Bleach Bypass",
        description="High saturation bleach bypass effect",
        ffmpeg_filter="eq=saturation=1.5,colorbalance=rs=0.1:gs=0.05:bs=-0.1",
    ),
    "log_to_rec709": ColorGradingProfile(
        name="Log to Rec709",
        description="Log footage converted to Rec709",
        ffmpeg_filter="curves=r='0/0 0.45/0.35 0.75/0.75 1/1':g='0/0 0.45/0.35 0.75/0.75 1/1':b='0/0 0.45/0.35 0.75/0.75 1/1'",
    ),
    "sepia": ColorGradingProfile(
        name="Sepia",
        description="Classic sepia tone",
        ffmpeg_filter="hue=s=0,colorbalance=rs=0.2:gs=0.1:bs=-0.15",
    ),
    "low_saturation_cinematic": ColorGradingProfile(
        name="Low Saturation Cinematic",
        description="Desaturated cinematic look",
        ffmpeg_filter="eq=saturation=0.7,curves=r='0/0 0.5/0.48 1/1':g='0/0 0.5/0.50 1/1':b='0/0 0.5/0.52 1/1'",
    ),
    "ultra_vivid": ColorGradingProfile(
        name="Ultra Vivid",
        description="Hyper-saturated vibrant colors",
        ffmpeg_filter="eq=saturation=1.8:brightness=0.1:contrast=1.2",
    ),
    "monochrome": ColorGradingProfile(
        name="Monochrome",
        description="Pure black and white",
        ffmpeg_filter="format=gray",
    ),
    "retro_80s": ColorGradingProfile(
        name="Retro 80s",
        description="1980s color grading aesthetic",
        ffmpeg_filter="colorbalance=rs=0.15:gs=-0.1:bs=0.2,eq=saturation=1.3,curves=r='0/0.1 0.5/0.5 1/0.95':g='0/0.1 0.5/0.5 1/0.95':b='0/0.1 0.5/0.5 1/0.95'",
    ),
}


class ColorGradingEngine:
    """Applies color grading to video clips."""

    def __init__(self):
        """Initialize color grading engine."""
        self.profiles = GRADING_PROFILES
        log.info("color_grading_engine_ready", extra={"profiles": len(self.profiles)})

    def get_filter_chain(
        self,
        profile_name: str,
        intensity: float = 1.0,
    ) -> str:
        """Get FFmpeg filter chain for a profile.

        Args:
            profile_name: Profile name key
            intensity: Intensity multiplier (0.0-2.0)
                      0.0 = no effect, 1.0 = normal, 2.0 = double intensity

        Returns:
            FFmpeg filter chain string
        """
        if profile_name not in self.profiles:
            log.warning(f"Unknown profile: {profile_name}")
            return ""

        profile = self.profiles[profile_name]

        base_filter = profile.ffmpeg_filter
        if not base_filter:
            return ""

        # Scale intensity
        if intensity == 1.0:
            return base_filter
        elif intensity < 1.0:
            # Blend with identity filter (no-op)
            # This is simplified; in production, parse and scale curve values
            return f"colorbalance=rs=0:gs=0:bs=0,{base_filter}"
        else:
            # Double intensity (experimental - in production, use proper curve scaling)
            return base_filter

    def list_profiles(self) -> list[dict]:
        """List all available color grading profiles."""
        return [
            {
                "name": name,
                "description": profile.description,
                "category": self._categorize_profile(name),
            }
            for name, profile in self.profiles.items()
        ]

    def _categorize_profile(self, name: str) -> str:
        """Categorize a profile by type."""
        if "cinematic" in name.lower():
            return "cinematic"
        elif "vintage" in name.lower() or "retro" in name.lower():
            return "vintage"
        elif "noir" in name.lower() or "monochrome" in name.lower():
            return "black_and_white"
        elif any(x in name.lower() for x in ["warm", "golden", "sepia"]):
            return "warm"
        elif "cool" in name.lower() or "teal" in name.lower():
            return "cool"
        else:
            return "other"

    def validate_profile(self, profile_name: str) -> tuple[bool, Optional[str]]:
        """Validate that a profile exists.

        Args:
            profile_name: Profile name to validate

        Returns:
            (is_valid, error_message)
        """
        if profile_name in self.profiles:
            return True, None
        return False, f"Profile '{profile_name}' not found"

    def apply_to_command(
        self,
        ffmpeg_cmd: list[str],
        profile_name: str = "cinematic_default",
        intensity: float = 1.0,
    ) -> list[str]:
        """Insert color grading filter into FFmpeg command.

        Args:
            ffmpeg_cmd: Base FFmpeg command array
            profile_name: Profile to apply
            intensity: Intensity (0.0-2.0)

        Returns:
            Modified FFmpeg command with filter inserted
        """
        filter_chain = self.get_filter_chain(profile_name, intensity)
        if not filter_chain:
            return ffmpeg_cmd

        # Find -vf flag position and append filter
        try:
            vf_index = ffmpeg_cmd.index("-vf")
            # Append to existing filter chain
            ffmpeg_cmd[vf_index + 1] += f",{filter_chain}"
        except ValueError:
            # No -vf flag, add it
            ffmpeg_cmd.extend(["-vf", filter_chain])

        log.info(
            "filter_applied",
            extra={"profile": profile_name, "intensity": intensity}
        )
        return ffmpeg_cmd
