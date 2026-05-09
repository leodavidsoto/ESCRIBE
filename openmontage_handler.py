"""
openmontage_handler.py — Interface para invocar OpenMontage compose desde master_orchestrator.

Envuelve la lógica de llamada a OpenMontage para evitar acoplamiento directo
en master_orchestrator. Abstrae el transporte HTTP + gestión de errores.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

log = logging.getLogger("openmontage_handler")


async def invoke_openmontage_compose(
    director_flow: dict[str, Any],
    clip_paths: list[Path],
    output_path: Path,
    timeout_seconds: int = 300,
) -> Path:
    """Invoca OpenMontage compose endpoint con director_flow + clips.

    Args:
        director_flow: Master Stack + scene plan completo (de openmontage_export.py)
        clip_paths: Lista de paths a videos MP4 generados (en orden escenas)
        output_path: Path donde guardar FINAL_CUT.mp4
        timeout_seconds: Timeout total para la operación (default 5 min)

    Returns:
        Path al video final generado (mismo que output_path si exitoso)

    Raises:
        RuntimeError: Si OpenMontage falla o no está disponible
    """
    try:
        import httpx  # type: ignore
    except ImportError as e:
        log.error("httpx_not_installed")
        raise RuntimeError("httpx required for OpenMontage invocation. pip install httpx.") from e

    # Obtener URL de OpenMontage desde env (debe estar configurado en bridge/main.py)
    openmontage_url = os.getenv("OPENMONTAGE_API_URL", "http://localhost:8000").rstrip("/")
    if not openmontage_url or openmontage_url.startswith("http://localhost:0"):
        log.error("openmontage_url_not_configured")
        raise RuntimeError(
            "OPENMONTAGE_API_URL not configured. "
            "Set it to http://openmontage:8000 or appropriate endpoint."
        )

    # Validar que todos los clips existen
    for i, cp in enumerate(clip_paths):
        if not cp.exists():
            raise FileNotFoundError(f"Clip {i} not found: {cp}")

    # Preparar payload para OpenMontage compose
    payload = {
        "scene_plan": director_flow,
        "clips": [{"path": str(p), "scene_id": f"scene-{i+1:03d}"} for i, p in enumerate(clip_paths)],
        "output_path": str(output_path),
        "format": "mp4",
        "codec": "h264",
        "quality": "high",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            log.info(
                "openmontage_compose_start",
                extra={
                    "url": f"{openmontage_url}/api/compose",
                    "clip_count": len(clip_paths),
                    "output": str(output_path),
                },
            )

            response = await client.post(
                f"{openmontage_url}/api/compose",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            response.raise_for_status()
            result = response.json()

            if result.get("status") == "success":
                final_path = result.get("output_path") or str(output_path)
                log.info(
                    "openmontage_compose_success",
                    extra={"output": final_path, "elapsed_s": result.get("elapsed_seconds")},
                )
                return Path(final_path)
            else:
                error_msg = result.get("error", "unknown error")
                log.error("openmontage_compose_failed", extra={"error": error_msg})
                raise RuntimeError(f"OpenMontage compose failed: {error_msg}")

    except httpx.TimeoutException as e:
        log.error("openmontage_timeout", extra={"timeout_s": timeout_seconds})
        raise RuntimeError(f"OpenMontage compose timeout after {timeout_seconds}s") from e
    except httpx.RequestError as e:
        log.error("openmontage_request_error", extra={"error": str(e)})
        raise RuntimeError(f"Failed to connect to OpenMontage at {openmontage_url}") from e
    except Exception as e:
        log.error("openmontage_compose_exception", extra={"error": str(e)})
        raise


def get_openmontage_health(timeout_seconds: int = 5) -> bool:
    """Verificar si OpenMontage endpoint está disponible (sync).

    Útil para la fase de preflight o para decidir fallback a moviepy.
    """
    try:
        import httpx  # type: ignore

        openmontage_url = os.getenv("OPENMONTAGE_API_URL", "http://localhost:8000").rstrip("/")
        if not openmontage_url or openmontage_url.startswith("http://localhost:0"):
            return False

        response = httpx.get(f"{openmontage_url}/health", timeout=timeout_seconds)
        return response.status_code == 200
    except Exception:
        return False
