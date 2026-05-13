"""
Visual effects engine for video composition.

Supports vignette, lens flare, motion blur, glitch, bokeh, and more.
"""
import logging
from dataclasses import dataclass
from typing import Callable, Literal, Optional

log = logging.getLogger("effects_engine")


@dataclass
class EffectDefinition:
    """Effect definition with FFmpeg filter."""
    name: str
    description: str
    ffmpeg_filter_builder: Callable[[float], str]
    intensity_range: tuple[float, float] = (0.0, 1.0)


def _fmt(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".") or "0"


# Predefined effects catalog
EFFECTS_CATALOG = {
    "vignette": EffectDefinition(
        name="Vignette",
        description="Darkened edges",
        ffmpeg_filter_builder=lambda intensity: f"vignette=angle={_fmt(3.14159 * intensity)}",
        intensity_range=(0.0, 1.0),
    ),
    "lens_flare": EffectDefinition(
        name="Lens Flare",
        description="Bright lens wash effect",
        ffmpeg_filter_builder=lambda intensity: (
            f"eq=brightness={_fmt(0.08 * intensity)}:saturation={_fmt(1 + 0.25 * intensity)}"
        ),
        intensity_range=(0.0, 1.0),
    ),
    "chromatic_aberration": EffectDefinition(
        name="Chromatic Aberration",
        description="RGB color separation",
        ffmpeg_filter_builder=lambda intensity: (
            f"chromashift=cbh={int(round(8 * intensity))}:crh={int(round(-8 * intensity))}:edge=wrap"
        ),
        intensity_range=(0.0, 1.0),
    ),
    "film_grain": EffectDefinition(
        name="Film Grain",
        description="Analog film grain texture",
        ffmpeg_filter_builder=lambda intensity: f"noise=alls={int(round(20 * intensity))}:allf=t",
        intensity_range=(0.0, 1.0),
    ),
    "motion_blur": EffectDefinition(
        name="Motion Blur",
        description="Soft directional blur",
        ffmpeg_filter_builder=lambda intensity: f"boxblur=lr={_fmt(5 * intensity)}:lp=1",
        intensity_range=(0.0, 1.0),
    ),
    "glitch": EffectDefinition(
        name="Glitch",
        description="Digital glitch effect",
        ffmpeg_filter_builder=lambda intensity: (
            f"rgbashift=rh={int(round(10 * intensity))}:bh={int(round(-10 * intensity))}:edge=wrap"
        ),
        intensity_range=(0.0, 1.0),
    ),
    "bokeh_bloom": EffectDefinition(
        name="Bokeh Bloom",
        description="Soft bokeh bloom effect",
        ffmpeg_filter_builder=lambda intensity: (
            f"gblur=sigma={_fmt(4 * intensity)},eq=brightness={_fmt(0.06 * intensity)}"
        ),
        intensity_range=(0.0, 1.0),
    ),
    "film_burn": EffectDefinition(
        name="Film Burn",
        description="Light leak film burn",
        ffmpeg_filter_builder=lambda intensity: (
            f"colorbalance=rs={_fmt(0.2 * intensity)}:gs={_fmt(0.1 * intensity)}:"
            f"bs={_fmt(-0.15 * intensity)},eq=brightness={_fmt(0.04 * intensity)}"
        ),
        intensity_range=(0.0, 1.0),
    ),
    "dust_particles": EffectDefinition(
        name="Dust Particles",
        description="Floating dust particle effect",
        ffmpeg_filter_builder=lambda intensity: (
            f"noise=alls={int(round(12 * intensity))}:allf=t,boxblur=lr=2:lp=1"
        ),
        intensity_range=(0.0, 1.0),
    ),
    "lens_distortion": EffectDefinition(
        name="Lens Distortion",
        description="Barrel or pincushion distortion",
        ffmpeg_filter_builder=lambda intensity: (
            f"lenscorrection=cx=0.5:cy=0.5:k1={_fmt(0.35 * intensity)}:"
            f"k2={_fmt(0.15 * intensity)}"
        ),
        intensity_range=(0.0, 1.0),
    ),
}


class EffectsEngine:
    """Manages visual effects for video composition."""

    def __init__(self):
        """Initialize effects engine."""
        self.effects = EFFECTS_CATALOG
        log.info("effects_engine_ready", extra={"effects": len(self.effects)})

    def get_filter(
        self,
        effect_name: str,
        intensity: float = 0.5,
    ) -> Optional[str]:
        """Get FFmpeg filter for an effect.

        Args:
            effect_name: Effect name key
            intensity: Effect intensity (0.0-1.0)

        Returns:
            FFmpeg filter string or None if effect not found
        """
        if effect_name not in self.effects:
            log.warning(f"Unknown effect: {effect_name}")
            return None

        effect = self.effects[effect_name]
        # Clamp intensity to range
        clamped = max(effect.intensity_range[0], min(effect.intensity_range[1], intensity))

        # Build filter string
        try:
            return effect.ffmpeg_filter_builder(clamped)
        except (TypeError, ValueError) as e:
            log.error(f"filter_format_error: {e}")
            return None

    def chain_effects(
        self,
        effects: list[dict],  # [{"name": "vignette", "intensity": 0.5}, ...]
    ) -> str:
        """Chain multiple effects into a single filter.

        Args:
            effects: List of effect definitions with intensity

        Returns:
            Combined FFmpeg filter chain
        """
        filters = []

        for effect_spec in effects:
            name = effect_spec.get("name")
            intensity = effect_spec.get("intensity", 0.5)

            filter_str = self.get_filter(name, intensity)
            if filter_str:
                filters.append(filter_str)

        result = ",".join(filters) if filters else ""
        log.info("effects_chained", extra={"count": len(filters), "chain": result[:100]})
        return result

    def list_effects(self) -> list[dict]:
        """List all available effects."""
        return [
            {
                "name": name,
                "description": effect.description,
                "intensity_range": effect.intensity_range,
            }
            for name, effect in self.effects.items()
        ]

    def validate_effect(self, effect_name: str) -> tuple[bool, Optional[str]]:
        """Validate that an effect exists.

        Args:
            effect_name: Effect name to validate

        Returns:
            (is_valid, error_message)
        """
        if effect_name in self.effects:
            return True, None
        return False, f"Effect '{effect_name}' not found"

    def apply_to_command(
        self,
        ffmpeg_cmd: list[str],
        effects: list[dict],
    ) -> list[str]:
        """Insert effects filter chain into FFmpeg command.

        Args:
            ffmpeg_cmd: Base FFmpeg command array
            effects: List of effect specs

        Returns:
            Modified FFmpeg command with effects inserted
        """
        filter_chain = self.chain_effects(effects)
        if not filter_chain:
            return ffmpeg_cmd

        try:
            vf_index = ffmpeg_cmd.index("-vf")
            ffmpeg_cmd[vf_index + 1] += f",{filter_chain}"
        except ValueError:
            ffmpeg_cmd.extend(["-vf", filter_chain])

        log.info("effects_applied", extra={"count": len(effects)})
        return ffmpeg_cmd
