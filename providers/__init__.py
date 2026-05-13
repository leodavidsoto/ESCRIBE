"""
Root provider package for ESCRIBE.

This package owns root-level integrations such as ``providers.muapi_gateway``
and re-exports the video provider factory implemented in Guion_expert.
"""
from Guion_expert.providers import (  # noqa: F401
    GenerationResult,
    ProviderError,
    VideoProvider,
    get_provider,
    resolve_provider_for_scene,
)

__all__ = [
    "GenerationResult",
    "ProviderError",
    "VideoProvider",
    "get_provider",
    "resolve_provider_for_scene",
]
