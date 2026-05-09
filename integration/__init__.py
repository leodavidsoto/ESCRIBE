"""
Integration module for ESCRIBE.

Provides compatibility layers and glue code for:
- Cinematography pipeline (color grading, effects, transitions)
- Muapi unified provider gateway
- Workflow studio system
"""

from .cinematography_pipeline import (
    apply_cinematography_to_scene,
    apply_transition,
    build_ffmpeg_filter_chain_from_director_flow,
)
from .muapi_integration import (
    generate_image,
    generate_video,
    generate_image_async,
    generate_video_async,
    get_available_models,
)

__all__ = [
    "apply_cinematography_to_scene",
    "apply_transition",
    "build_ffmpeg_filter_chain_from_director_flow",
    "generate_image",
    "generate_video",
    "generate_image_async",
    "generate_video_async",
    "get_available_models",
]
