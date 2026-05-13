"""
Muapi.ai unified provider gateway for ESCRIBE.

Abstraction layer over 200+ AI models through Muapi.ai API.
Replaces Trinity + FAL with single configurable interface.
"""
import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Literal, Optional
from dataclasses import dataclass

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

log = logging.getLogger("muapi_gateway")

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass
class GenerationResult:
    """Result from any provider (image or video generation)."""
    success: bool
    output_path: Optional[Path] = None
    error: Optional[str] = None
    model: Optional[str] = None
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MuapiGateway:
    """Unified interface to 200+ models via Muapi.ai."""

    # Model registrations
    TEXT_TO_IMAGE = {
        "flux-pro": "flux-pro",
        "flux-standard": "flux-dev",
        "flux-realism": "flux-realism",
        "midjourney": "midjourney-v6",
        "dall-e-3": "dall-e-3",
    }

    IMAGE_TO_IMAGE = {
        "flux-pro-i2i": "flux-pro-i2i",
        "flux-inpaint": "flux-inpaint",
        "stable-diffusion-xl": "sdxl-turbo",
    }

    TEXT_TO_VIDEO = {
        "sora": "sora-1",
        "kling": "kling-v1.5",
        "veo": "veo-2",
        "runway-gen3": "runway-gen3-alpha",
    }

    IMAGE_TO_VIDEO = {
        "runway-i2v": "runway-i2v",
        "veo-i2v": "veo-2-i2v",
        "kling-i2v": "kling-v1.5-i2v",
        "luma-dream": "luma-dream-machine",
    }

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """Initialize Muapi gateway.

        Args:
            api_key: Muapi API key (defaults to MUAPI_KEY env var)
            base_url: Muapi API base URL (defaults to official endpoint)
        """
        if not HAS_HTTPX:
            raise RuntimeError("httpx required. pip install httpx")

        self.api_key = api_key or os.getenv("MUAPI_KEY")
        self.base_url = base_url or "https://api.muapi.ai/v1"
        self.client = httpx.AsyncClient(timeout=600)

        if not self.api_key:
            log.warning("MUAPI_KEY not configured; generation will fail")

    def _output_path(self, prefix: str, seed: str, suffix: str) -> Path:
        safe_seed = _SAFE_FILENAME_RE.sub("-", seed).strip("._-")[:48] or "output"
        return Path("/tmp") / f"escribe_{prefix}_{safe_seed}{suffix}"

    def _extract_output_url(self, payload: Any) -> Optional[str]:
        if isinstance(payload, str) and payload.startswith(("http://", "https://")):
            return payload
        if isinstance(payload, dict):
            for key in ("url", "output_url", "image_url", "video_url", "audio_url"):
                value = payload.get(key)
                if isinstance(value, str) and value.startswith(("http://", "https://")):
                    return value
            for key in ("data", "output", "outputs", "result", "results"):
                nested = payload.get(key)
                found = self._extract_output_url(nested)
                if found:
                    return found
        if isinstance(payload, list):
            for item in payload:
                found = self._extract_output_url(item)
                if found:
                    return found
        return None

    async def _download_output(self, url: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        async with self.client.stream("GET", url, follow_redirects=True) as response:
            response.raise_for_status()
            with output_path.open("wb") as handle:
                async for chunk in response.aiter_bytes():
                    if chunk:
                        handle.write(chunk)
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError(f"Downloaded output is empty: {url}")
        return output_path

    async def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        image_input: Optional[Path] = None,
        width: int = 1024,
        height: int = 1024,
        steps: int = 30,
        guidance_scale: float = 7.5,
    ) -> GenerationResult:
        """Generate or transform an image.

        Auto-selects T2I or I2I based on image_input presence.

        Args:
            prompt: Text description
            model: Model key (auto-selects best T2I/I2I if None)
            image_input: Input image for I2I (triggers I2I mode)
            width, height: Output dimensions
            steps: Inference steps (20-50)
            guidance_scale: Guidance strength (1-20)

        Returns:
            GenerationResult with output_path or error
        """
        try:
            # Auto-route to I2I if image provided
            if image_input:
                if not image_input.exists():
                    return GenerationResult(
                        success=False,
                        error=f"Input image not found: {image_input}"
                    )
                model = model or "flux-pro-i2i"
                return await self._invoke_i2i(
                    prompt, model, image_input, width, height, steps, guidance_scale
                )
            else:
                # T2I mode
                model = model or "flux-pro"
                return await self._invoke_t2i(
                    prompt, model, width, height, steps, guidance_scale
                )

        except Exception as e:
            log.error("image_generation_failed", extra={"error": str(e)})
            return GenerationResult(success=False, error=str(e))

    async def generate_video(
        self,
        prompt: Optional[str] = None,
        image_input: Optional[Path] = None,
        model: Optional[str] = None,
        duration: float = 5.0,
        fps: int = 24,
        resolution: Literal["720p", "1080p", "4k"] = "1080p",
    ) -> GenerationResult:
        """Generate or extend video.

        Auto-selects T2V or I2V based on image_input presence.

        Args:
            prompt: Text description (required for T2V)
            image_input: Input image for I2V (triggers I2V mode)
            model: Model key (auto-selects best if None)
            duration: Video length in seconds
            fps: Frames per second
            resolution: Output resolution

        Returns:
            GenerationResult with output_path or error
        """
        try:
            if image_input:
                if not image_input.exists():
                    return GenerationResult(
                        success=False,
                        error=f"Input image not found: {image_input}"
                    )
                model = model or "runway-i2v"
                return await self._invoke_i2v(
                    image_input, prompt, model, duration, fps, resolution
                )
            else:
                if not prompt:
                    return GenerationResult(
                        success=False,
                        error="prompt required for T2V mode"
                    )
                model = model or "sora"
                return await self._invoke_t2v(
                    prompt, model, duration, fps, resolution
                )

        except Exception as e:
            log.error("video_generation_failed", extra={"error": str(e)})
            return GenerationResult(success=False, error=str(e))

    async def _invoke_t2i(
        self, prompt: str, model: str, width: int, height: int,
        steps: int, guidance: float
    ) -> GenerationResult:
        """Text-to-Image via Muapi."""
        payload = {
            "model": self.TEXT_TO_IMAGE.get(model, model),
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
        }

        response = await self.client.post(
            f"{self.base_url}/images/generations",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )

        if response.status_code != 200:
            return GenerationResult(
                success=False,
                error=f"Muapi T2I failed: {response.text}"
            )

        result = response.json()
        output_url = self._extract_output_url(result)
        if not output_url:
            return GenerationResult(
                success=False,
                error="Muapi T2I response did not include an output URL",
                metadata=result,
            )
        output_path = await self._download_output(
            output_url,
            self._output_path("image", prompt[:30], ".png"),
        )
        log.info("t2i_success", extra={"model": model, "output": str(output_path)})

        return GenerationResult(
            success=True,
            output_path=output_path,
            model=model,
            metadata={
                **(result.get("metadata", {}) if isinstance(result, dict) else {}),
                "output_url": output_url,
            }
        )

    async def _invoke_i2i(
        self, prompt: str, model: str, image_input: Path,
        width: int, height: int, steps: int, guidance: float
    ) -> GenerationResult:
        """Image-to-Image via Muapi."""
        with open(image_input, "rb") as f:
            image_data = f.read()

        files = {"image": ("input.png", image_data, "image/png")}
        data = {
            "model": self.IMAGE_TO_IMAGE.get(model, model),
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
        }

        response = await self.client.post(
            f"{self.base_url}/images/edits",
            data=data,
            files=files,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )

        if response.status_code != 200:
            return GenerationResult(
                success=False,
                error=f"Muapi I2I failed: {response.text}"
            )

        result = response.json()
        output_url = self._extract_output_url(result)
        if not output_url:
            return GenerationResult(
                success=False,
                error="Muapi I2I response did not include an output URL",
                metadata=result,
            )
        output_path = await self._download_output(
            output_url,
            self._output_path("image_i2i", image_input.stem, ".png"),
        )

        log.info("i2i_success", extra={"model": model, "output": str(output_path)})

        return GenerationResult(
            success=True,
            output_path=output_path,
            model=model,
            metadata={
                **(result.get("metadata", {}) if isinstance(result, dict) else {}),
                "output_url": output_url,
            }
        )

    async def _invoke_t2v(
        self, prompt: str, model: str, duration: float, fps: int, resolution: str
    ) -> GenerationResult:
        """Text-to-Video via Muapi."""
        payload = {
            "model": self.TEXT_TO_VIDEO.get(model, model),
            "prompt": prompt,
            "duration": duration,
            "fps": fps,
            "resolution": resolution,
        }

        response = await self.client.post(
            f"{self.base_url}/videos/generations",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )

        if response.status_code not in (200, 202):  # 202 = async
            return GenerationResult(
                success=False,
                error=f"Muapi T2V failed: {response.text}"
            )

        result = response.json()
        output_url = self._extract_output_url(result)
        if output_url:
            output_path = await self._download_output(
                output_url,
                self._output_path("video", Path(prompt[:30]).name, ".mp4"),
            )
            return GenerationResult(
                success=True,
                output_path=output_path,
                model=model,
                metadata={
                    **(result.get("metadata", {}) if isinstance(result, dict) else {}),
                    "output_url": output_url,
                },
            )
        # Poll for completion if async
        job_id = result.get("id") if isinstance(result, dict) else None
        output_path = await self._poll_job(job_id, model)

        if not output_path:
            return GenerationResult(
                success=False,
                error=f"T2V job {job_id} failed or timed out"
            )

        log.info("t2v_success", extra={"model": model, "output": str(output_path)})

        return GenerationResult(
            success=True,
            output_path=output_path,
            model=model,
            metadata=result.get("metadata", {}) if isinstance(result, dict) else {}
        )

    async def _invoke_i2v(
        self, image_input: Path, prompt: Optional[str], model: str,
        duration: float, fps: int, resolution: str
    ) -> GenerationResult:
        """Image-to-Video via Muapi."""
        with open(image_input, "rb") as f:
            image_data = f.read()

        files = {"image": ("input.png", image_data, "image/png")}
        data = {
            "model": self.IMAGE_TO_VIDEO.get(model, model),
            "duration": duration,
            "fps": fps,
            "resolution": resolution,
        }
        if prompt:
            data["prompt"] = prompt

        response = await self.client.post(
            f"{self.base_url}/videos/generations",
            data=data,
            files=files,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )

        if response.status_code not in (200, 202):
            return GenerationResult(
                success=False,
                error=f"Muapi I2V failed: {response.text}"
            )

        result = response.json()
        output_url = self._extract_output_url(result)
        if output_url:
            output_path = await self._download_output(
                output_url,
                self._output_path("video_i2v", image_input.stem, ".mp4"),
            )
            return GenerationResult(
                success=True,
                output_path=output_path,
                model=model,
                metadata={
                    **(result.get("metadata", {}) if isinstance(result, dict) else {}),
                    "output_url": output_url,
                },
            )
        job_id = result.get("id") if isinstance(result, dict) else None
        output_path = await self._poll_job(job_id, model)

        if not output_path:
            return GenerationResult(
                success=False,
                error=f"I2V job {job_id} failed or timed out"
            )

        log.info("i2v_success", extra={"model": model, "output": str(output_path)})

        return GenerationResult(
            success=True,
            output_path=output_path,
            model=model,
            metadata=result.get("metadata", {}) if isinstance(result, dict) else {}
        )

    async def _poll_job(self, job_id: str, model: str, timeout: int = 600) -> Optional[Path]:
        """Poll Muapi job until completion."""
        if not job_id:
            return None
        start = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start < timeout:
            response = await self.client.get(
                f"{self.base_url}/jobs/{job_id}",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )

            if response.status_code != 200:
                await asyncio.sleep(5)
                continue

            result = response.json()
            status = result.get("status")

            if status == "completed":
                output_url = self._extract_output_url(result)
                if not output_url:
                    log.error("job_completed_without_output_url", extra={"job_id": job_id})
                    return None
                output_path = self._output_path("video", job_id, ".mp4")
                return await self._download_output(output_url, output_path)

            elif status == "failed":
                log.error("job_failed", extra={"job_id": job_id, "error": result.get("error")})
                return None

            await asyncio.sleep(10)

        log.error("job_timeout", extra={"job_id": job_id, "model": model})
        return None

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
