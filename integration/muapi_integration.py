"""
Integration module for Muapi unified provider gateway.

Provides compatibility layer between master_orchestrator and Muapi gateway.
"""
import asyncio
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("muapi_integration")


def _get_muapi_gateway():
    """Lazy load Muapi gateway."""
    try:
        from providers.muapi_gateway import MuapiGateway
        return MuapiGateway()
    except (ImportError, RuntimeError) as e:
        log.warning("muapi_gateway_not_available", extra={"error": str(e)})
        return None


async def generate_image_async(
    prompt: str,
    model: Optional[str] = None,
    image_input: Optional[Path] = None,
    width: int = 1024,
    height: int = 1024,
) -> Optional[Path]:
    """Generate image via Muapi gateway.

    Args:
        prompt: Image description
        model: Model key (auto-selects if None)
        image_input: Input image for I2I mode (optional)
        width: Output width
        height: Output height

    Returns:
        Path to generated image or None if failed
    """
    gateway = _get_muapi_gateway()
    if not gateway:
        log.warning("muapi_not_available_cannot_generate_image")
        return None

    try:
        result = await gateway.generate_image(
            prompt=prompt,
            model=model,
            image_input=image_input,
            width=width,
            height=height,
        )

        if result.success:
            log.info("muapi_image_generated", extra={"model": result.model, "output": str(result.output_path)})
            return result.output_path
        else:
            log.error("muapi_image_generation_failed", extra={"error": result.error})
            return None

    except Exception as e:
        log.error("muapi_image_generation_exception", extra={"error": str(e)})
        return None
    finally:
        await gateway.close()


async def generate_video_async(
    prompt: Optional[str] = None,
    image_input: Optional[Path] = None,
    model: Optional[str] = None,
    duration: float = 5.0,
    fps: int = 24,
    resolution: str = "1080p",
) -> Optional[Path]:
    """Generate video via Muapi gateway.

    Args:
        prompt: Video description (required for T2V)
        image_input: Input image for I2V mode (optional)
        model: Model key (auto-selects if None)
        duration: Video duration in seconds
        fps: Frames per second
        resolution: Output resolution (720p, 1080p, 4k)

    Returns:
        Path to generated video or None if failed
    """
    gateway = _get_muapi_gateway()
    if not gateway:
        log.warning("muapi_not_available_cannot_generate_video")
        return None

    try:
        result = await gateway.generate_video(
            prompt=prompt,
            image_input=image_input,
            model=model,
            duration=duration,
            fps=fps,
            resolution=resolution,
        )

        if result.success:
            log.info("muapi_video_generated", extra={"model": result.model, "output": str(result.output_path)})
            return result.output_path
        else:
            log.error("muapi_video_generation_failed", extra={"error": result.error})
            return None

    except Exception as e:
        log.error("muapi_video_generation_exception", extra={"error": str(e)})
        return None
    finally:
        await gateway.close()


def generate_image(
    prompt: str,
    model: Optional[str] = None,
    image_input: Optional[Path] = None,
    width: int = 1024,
    height: int = 1024,
) -> Optional[Path]:
    """Synchronous wrapper for image generation.

    Args:
        prompt: Image description
        model: Model key
        image_input: Input image for I2I
        width: Output width
        height: Output height

    Returns:
        Path to generated image or None
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context, create task
            task = asyncio.create_task(generate_image_async(prompt, model, image_input, width, height))
            return loop.run_until_complete(task)
        else:
            # Create new event loop
            return loop.run_until_complete(generate_image_async(prompt, model, image_input, width, height))
    except RuntimeError:
        # No event loop, create new one
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(generate_image_async(prompt, model, image_input, width, height))
        finally:
            new_loop.close()


def generate_video(
    prompt: Optional[str] = None,
    image_input: Optional[Path] = None,
    model: Optional[str] = None,
    duration: float = 5.0,
    fps: int = 24,
    resolution: str = "1080p",
) -> Optional[Path]:
    """Synchronous wrapper for video generation.

    Args:
        prompt: Video description
        image_input: Input image for I2V
        model: Model key
        duration: Duration in seconds
        fps: Frames per second
        resolution: Output resolution

    Returns:
        Path to generated video or None
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context, create task
            task = asyncio.create_task(generate_video_async(prompt, image_input, model, duration, fps, resolution))
            return loop.run_until_complete(task)
        else:
            # Run in existing loop
            return loop.run_until_complete(generate_video_async(prompt, image_input, model, duration, fps, resolution))
    except RuntimeError:
        # No event loop, create new one
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            return new_loop.run_until_complete(generate_video_async(prompt, image_input, model, duration, fps, resolution))
        finally:
            new_loop.close()


def get_available_models() -> dict:
    """Get available models from Muapi gateway.

    Returns:
        Dict with model categories and available models
    """
    gateway = _get_muapi_gateway()
    if not gateway:
        return {}

    return {
        "text_to_image": list(gateway.TEXT_TO_IMAGE.keys()),
        "image_to_image": list(gateway.IMAGE_TO_IMAGE.keys()),
        "text_to_video": list(gateway.TEXT_TO_VIDEO.keys()),
        "image_to_video": list(gateway.IMAGE_TO_VIDEO.keys()),
    }
