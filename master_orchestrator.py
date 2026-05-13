"""
master_orchestrator.py — Pipeline end-to-end: Guion → VeoPrompt → Assets → Edit.

v2 — Trinity hybrid
-------------------
Cambios vs. v1:
  • Ya no se genera Python como string mediante f-string templates.
  • Usa providers/ (get_provider + resolve_provider_for_scene) para que
    el routing fal/trinity sea transparente.
  • Respeta preferred_backend emitido por el director_flow por escena.
  • I2V genera FLUX ancla + video. T2V salta FLUX (más rápido + barato).
  • Fallback automático: si Trinity falla, cae a fal.ai sin drama.
  • Paths derivados de env vars (GUION_EXPERT_DIR, OPENMONTAGE_DIR) —
    ya no están hardcoded a /Users/mac/.

Uso:
    # modo idea → pipeline total
    python master_orchestrator.py -i "Una chica descubre una carta vieja"

    # modo proyecto ya existente
    python master_orchestrator.py -p /ruta/output/0034_2026-04-22T1245

Variables de entorno relevantes:
    GUION_EXPERT_DIR       (default: ./Guion_expert)
    OPENMONTAGE_DIR        (default: ./OpenMontage/OpenMontage)
    TRINITY_ENABLED        false|true (default false)
    TRINITY_URL            URL del túnel del Colab
    TRINITY_TOKEN          shared secret
    FAL_API_KEY            key para fal.ai
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ────────────────────────────────────────────────────────────────────────
# Bootstrap paths (env vars con fallback relativo al working dir)
# ────────────────────────────────────────────────────────────────────────

_here = Path(__file__).resolve().parent
GUION_EXPERT_DIR = Path(os.getenv("GUION_EXPERT_DIR") or (_here / "Guion_expert"))
OPENMONTAGE_DIR = Path(os.getenv("OPENMONTAGE_DIR") or (_here / "OpenMontage" / "OpenMontage"))


def _prepend_sys_path(path: Path) -> None:
    path_str = str(path)
    if path_str in sys.path:
        sys.path.remove(path_str)
    sys.path.insert(0, path_str)


# Repo root must win for root packages such as providers/.
for _path in (
    GUION_EXPERT_DIR / "bridge",
    GUION_EXPERT_DIR / "webapp",
    GUION_EXPERT_DIR,
    _here,
):
    _prepend_sys_path(_path)


def _create_celery_app():
    """Create the Celery app used by the Procfile worker when Celery exists."""
    try:
        from celery import Celery  # type: ignore
    except ImportError:
        class CeleryUnavailable:
            main = "master_orchestrator"

            def __repr__(self) -> str:
                return "<Celery unavailable: install celery to run workers>"

        return CeleryUnavailable()

    broker_url = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "memory://"
    result_backend = os.getenv("CELERY_RESULT_BACKEND") or os.getenv("REDIS_URL") or "cache+memory://"
    app = Celery("master_orchestrator", broker=broker_url, backend=result_backend)
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone=os.getenv("CELERY_TIMEZONE", "UTC"),
        enable_utc=True,
    )
    return app


celery_app = _create_celery_app()

# Import CLIP validator for Flux feedback loop
def _load_clip_validator():
    """Lazy load CLIP validator to avoid import failures if not needed."""
    try:
        from i2V.apps.api.src.i2v_api.clip_validator import validate_flux_image
        return validate_flux_image, True
    except ImportError:
        # Try alternative path structure
        try:
            i2v_path = _here / "i2V" / "apps" / "api" / "src"
            if i2v_path.exists():
                sys.path.insert(0, str(i2v_path))
                from i2v_api.clip_validator import validate_flux_image
                return validate_flux_image, True
        except (ImportError, AttributeError):
            pass
        return None, False

validate_flux_image, CLIP_AVAILABLE = _load_clip_validator()

from webapp.pipeline_claude import run_full_pipeline  # noqa: E402
from bridge.openmontage_export import export_project_to_openmontage  # noqa: E402
from providers import get_provider, resolve_provider_for_scene, ProviderError  # noqa: E402

# Import OpenMontage handler (may not be available, fallback to moviepy)
try:
    from openmontage_handler import invoke_openmontage_compose, get_openmontage_health
    OPENMONTAGE_AVAILABLE = True
except ImportError:
    OPENMONTAGE_AVAILABLE = False
    invoke_openmontage_compose = None
    get_openmontage_health = None


# ────────────────────────────────────────────────────────────────────────
# Logging
# ────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("master_orchestrator")


# ────────────────────────────────────────────────────────────────────────
# FLUX ancla (solo para escenas I2V)
# ────────────────────────────────────────────────────────────────────────

def _generate_flux_anchor(prompt: str, output_path: Path, formato: str = "CORTO") -> bool:
    """Genera la imagen ancla con FLUX.1 Pro via fal.ai.

    Incluye validación CLIP: regenera si similitud < 0.25 (max 2 reintentos).
    Retorna True si se generó (o ya existía). False si falló.
    """
    if output_path.exists():
        return True
    try:
        # Import local para no costar nada si la escena es T2V pura.
        import requests  # type: ignore
    except ImportError:
        log.error("requests_not_installed_cannot_call_flux")
        return False

    api_key = os.getenv("FAL_API_KEY", "")
    if not api_key or api_key.startswith("REEMPLAZAR"):
        log.error("flux_skipped_no_fal_api_key")
        return False

    # Aspecto según formato
    is_vertical = "REEL" in formato.upper() or "STORY" in formato.upper() or "TIKTOK" in formato.upper()
    width, height = (1080, 1920) if is_vertical else (1920, 1080)

    submit_url = f"{os.getenv('FAL_BASE_URL', 'https://queue.fal.run')}/fal-ai/flux-pro/v1.1"
    headers = {"Authorization": f"Key {api_key}", "Content-Type": "application/json"}

    # CLIP validation threshold (regenerate if below)
    clip_threshold = float(os.getenv("FLUX_CLIP_THRESHOLD", "0.25"))
    max_clip_retries = int(os.getenv("FLUX_CLIP_RETRIES", "2"))

    def _call_flux(current_prompt: str) -> bytes | None:
        """Helper: realiza una llamada a FLUX y retorna bytes de imagen o None si falla."""
        payload = {
            "prompt": current_prompt,
            "image_size": {"width": width, "height": height},
            "num_inference_steps": int(os.getenv("FLUX_STEPS", "28")),
            "guidance_scale": float(os.getenv("FLUX_GUIDANCE", "3.5")),
            "num_images": 1,
            "enable_safety_checker": False,
        }
        try:
            r = requests.post(submit_url, json=payload, headers=headers, timeout=(10.0, 180.0))
            r.raise_for_status()
            data = r.json()
            status_url = data.get("status_url") or data.get("response_url")
            if not status_url:
                log.error("flux_no_status_url", extra={"body": data})
                return None
            # Poll
            import time
            for _ in range(60):
                pr = requests.get(status_url, headers=headers, timeout=(10.0, 30.0))
                pr.raise_for_status()
                st = pr.json()
                if st.get("status") in ("COMPLETED", "completed"):
                    result_url = st.get("response_url") or status_url
                    rr = requests.get(result_url, headers=headers, timeout=(10.0, 30.0))
                    rr.raise_for_status()
                    image_url = rr.json().get("images", [{}])[0].get("url")
                    if not image_url:
                        return None
                    img_bytes = requests.get(image_url, timeout=(10.0, 120.0)).content
                    return img_bytes
                if st.get("status") in ("FAILED", "failed"):
                    log.error("flux_failed", extra={"status": st})
                    return None
                time.sleep(3.0)
            log.error("flux_timeout")
            return None
        except Exception as e:
            log.error("flux_call_exception", extra={"error": str(e)})
            return None

    # Generar imagen inicial
    img_bytes = _call_flux(prompt)
    if not img_bytes:
        return False

    # Guardar temporalmente para validación CLIP
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(img_bytes)

    # ─── Validación CLIP: regenerar si score bajo ─────────────────────
    if CLIP_AVAILABLE:
        try:
            similarity, is_valid = validate_flux_image(output_path, prompt, threshold=clip_threshold)
            log.info("flux_clip_validation",
                     extra={"similarity": f"{similarity:.3f}", "valid": is_valid, "threshold": clip_threshold})

            # Si score bajo, reintentar con prompt mejorado (max 2 veces)
            retry_count = 0
            while not is_valid and retry_count < max_clip_retries:
                retry_count += 1
                refined_prompt = f"{prompt} (more detailed, specific, high quality, vivid colors)"
                log.info("flux_clip_retry",
                         extra={"retry": retry_count, "max": max_clip_retries, "refined_prompt": refined_prompt[:100]})

                new_bytes = _call_flux(refined_prompt)
                if not new_bytes:
                    log.warning("flux_clip_retry_generation_failed")
                    break

                # Guardar nueva imagen y validar
                output_path.write_bytes(new_bytes)
                similarity, is_valid = validate_flux_image(output_path, prompt, threshold=clip_threshold)
                log.info("flux_clip_retry_validation",
                         extra={"retry": retry_count, "similarity": f"{similarity:.3f}", "valid": is_valid})

            if not is_valid:
                log.warning("flux_clip_below_threshold_accepted_anyway",
                           extra={"similarity": f"{similarity:.3f}", "threshold": clip_threshold})
        except Exception as e:
            log.warning("flux_clip_validation_error", extra={"error": str(e)})
            # Continuar aunque falte validación CLIP
    else:
        log.info("flux_clip_not_available_skipping_validation")

    return True


# ────────────────────────────────────────────────────────────────────────
# Procesamiento por escena (paralelo)
# ────────────────────────────────────────────────────────────────────────

def _process_scene(scene: dict, assets_dir: Path, formato: str) -> str | None:
    """Genera la imagen ancla (si I2V) y el video para una escena.

    Usa:
      - scene["master_stack"]["modality"]: i2v | t2v
      - scene["master_stack"]["needs_flux_anchor"]: bool
      - scene["master_stack"]["chosen_video_model"]
      - resolve_provider_for_scene(): respeta preferred_backend
    """
    scene_id = scene.get("id", scene.get("scene_id"))
    if not scene_id:
        log.warning("scene_no_id", extra={"scene": scene})
        return None

    ms = scene.get("master_stack")
    if not ms:
        log.warning("scene_no_master_stack", extra={"scene_id": scene_id})
        return None

    modality = ms.get("modality", "i2v")
    needs_flux = ms.get("needs_flux_anchor", modality == "i2v")
    model = ms.get("chosen_video_model", "kling-2.5-pro")
    backend = ms.get("backend", "fal")
    routing_reason = ms.get("routing_reason", "")

    visual = ms.get("visual_anchor") or {}
    motion = ms.get("motion_intent") or {}
    camera = ms.get("camera") or {}

    flux_prompt = visual.get("flux_prompt") or ""
    video_prompt = motion.get("action") or flux_prompt or "Cinematic motion"
    duration = float(camera.get("duration_seconds") or 5.0)

    # Aspect ratio por formato
    is_vertical = "REEL" in formato.upper() or "STORY" in formato.upper() or "TIKTOK" in formato.upper()
    aspect_ratio = "9:16" if is_vertical else "16:9"

    img_path = assets_dir / f"{scene_id}-flux.jpg"
    vid_path = assets_dir / f"{scene_id}-video.mp4"

    log.info(
        "scene_start",
        extra={"scene_id": scene_id, "model": model, "backend": backend,
               "modality": modality, "routing_reason": routing_reason},
    )

    # ─── 1. FLUX ancla (solo I2V) ─────────────────────────────────────
    if needs_flux and not img_path.exists():
        ok = _generate_flux_anchor(flux_prompt, img_path, formato=formato)
        if not ok:
            log.error("flux_failed_skipping", extra={"scene_id": scene_id})
            return None

    # ─── 2. Video (I2V o T2V según modalidad) ─────────────────────────
    if vid_path.exists():
        log.info("video_cached", extra={"scene_id": scene_id})
        return scene_id

    provider = resolve_provider_for_scene(scene)
    try:
        if modality == "i2v":
            result = provider.generate_i2v(
                image_path=img_path,
                prompt=video_prompt,
                model=model,
                duration_seconds=duration,
                aspect_ratio=aspect_ratio,
                output_path=vid_path,
            )
        else:  # t2v
            result = provider.generate_t2v(
                prompt=flux_prompt or video_prompt,  # t2v usa el prompt denso
                model=model,
                duration_seconds=duration,
                aspect_ratio=aspect_ratio,
                output_path=vid_path,
            )
        log.info(
            "scene_done",
            extra={"scene_id": scene_id, "backend_used": result.backend,
                   "model_used": result.model, "modality": result.modality,
                   "latency_s": round(result.latency_seconds, 1)},
        )
        return scene_id
    except ProviderError as e:
        log.error(
            "scene_failed",
            extra={"scene_id": scene_id, "backend": e.backend, "error": str(e),
                   "retriable": e.retriable},
        )
        return None
    except Exception as e:
        log.error("scene_failed_unexpected", extra={"scene_id": scene_id, "error": str(e)})
        return None


def run_asset_director(scene_plan_path: Path, assets_dir: Path, formato: str,
                       max_workers: int = 4) -> dict:
    """Ejecuta la fase 3 (generación de assets) en paralelo sobre todas las escenas."""
    assets_dir.mkdir(parents=True, exist_ok=True)
    scene_plan = json.loads(scene_plan_path.read_text(encoding="utf-8"))
    scenes = scene_plan.get("scenes") or scene_plan.get("master_assets") or []

    if not scenes:
        log.warning("no_scenes_in_plan")
        return {"ok": [], "failed": []}

    # Boot provider (logs la elección una sola vez)
    provider = get_provider()
    log.info("provider_booted", extra={"name": provider.name,
                                        "healthy": provider.is_healthy()})

    ok_scenes: list[str] = []
    failed_scenes: list[str] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_process_scene, s, assets_dir, formato): s.get("id")
            for s in scenes
        }
        for fut in as_completed(futures):
            sid = futures[fut]
            result = fut.result()
            if result:
                ok_scenes.append(result)
            else:
                failed_scenes.append(sid)

    log.info("asset_director_done",
             extra={"ok": len(ok_scenes), "failed": len(failed_scenes)})
    return {"ok": ok_scenes, "failed": failed_scenes}


# ────────────────────────────────────────────────────────────────────────
# Edit final (moviepy concat)
# ────────────────────────────────────────────────────────────────────────

def run_edit_director(scene_plan_path: Path, assets_dir: Path,
                      output_path: Path) -> Path:
    """Composición final: usa OpenMontage si disponible, fallback a moviepy.

    Fase 4: Aplica color grading, transiciones y efectos cinematográficos
    a partir del director_flow almacenado en scene_plan.json.
    """
    scene_plan = json.loads(scene_plan_path.read_text(encoding="utf-8"))
    scenes = scene_plan.get("scenes") or scene_plan.get("master_assets") or []

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Recolectar clip paths (en orden)
    clip_paths = []
    for scene in scenes:
        sid = scene.get("id", scene.get("scene_id"))
        vp = assets_dir / f"{sid}-video.mp4"
        if vp.exists():
            clip_paths.append(vp)
            log.info("clip_collected", extra={"scene_id": sid, "path": str(vp)})
        else:
            log.warning("clip_missing", extra={"scene_id": sid})

    if not clip_paths:
        raise RuntimeError("No hay clips para concatenar — revisá los errores de la Fase 3.")

    # ─── Intento 1: OpenMontage (si disponible) ─────────────────────────
    if OPENMONTAGE_AVAILABLE and get_openmontage_health():
        try:
            log.info("edit_director_using_openmontage",
                     extra={"clip_count": len(clip_paths), "output": str(output_path)})

            # Preparar director_flow (toda la metadata cinematográfica del scene_plan)
            director_flow = {
                "scenes": scenes,
                "metadata": scene_plan.get("metadata", {}),
            }

            # Invocar OpenMontage (llamada síncrona via asyncio.run)
            import asyncio
            result = asyncio.run(
                invoke_openmontage_compose(
                    director_flow=director_flow,
                    clip_paths=clip_paths,
                    output_path=output_path,
                    timeout_seconds=600,  # 10 min para composición
                )
            )
            log.info("edit_director_openmontage_success", extra={"output": str(result)})
            return result

        except Exception as e:
            log.warning("edit_director_openmontage_failed",
                       extra={"error": str(e), "fallback": "moviepy"})
            # Continuar a fallback moviepy

    # ─── Fallback: MoviePy (simple concatenación) ──────────────────────
    try:
        from moviepy import VideoFileClip, concatenate_videoclips  # type: ignore
    except ImportError:
        try:
            from moviepy.editor import VideoFileClip, concatenate_videoclips  # type: ignore
        except ImportError as e:
            log.error("moviepy_not_installed")
            raise RuntimeError("moviepy no instalado. pip install moviepy.") from e

    try:
        clips = []
        for vp in clip_paths:
            try:
                clips.append(VideoFileClip(str(vp)))
                log.info("clip_loaded_moviepy", extra={"path": str(vp)})
            except Exception as e:
                log.error("clip_load_failed_moviepy", extra={"path": str(vp), "error": str(e)})

        if not clips:
            raise RuntimeError("No clips cargados en MoviePy.")

        log.info("concat_start_moviepy", extra={"clip_count": len(clips)})
        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            fps=24,
            preset="fast",
            logger=None,
        )
        log.info("concat_done_moviepy", extra={"output": str(output_path)})
        return output_path

    except Exception as e:
        log.error("moviepy_concat_failed", extra={"error": str(e)})
        raise RuntimeError(f"MoviePy concatenation failed: {e}") from e


# ────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="OpenMontage Master Orchestrator (v2 Trinity hybrid)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-i", "--idea", help="La idea del guion para ejecutar el pipeline total.")
    group.add_argument("-p", "--project", help="Ruta a una carpeta output/XXXX ya generada.")
    parser.add_argument("--max-workers", type=int, default=4,
                        help="Threads paralelos en la fase de assets (default 4).")
    parser.add_argument("--skip-edit", action="store_true",
                        help="No concatenar el FINAL_CUT al final.")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("MASTER ORCHESTRATOR v2 — Trinity hybrid")
    log.info("GUION_EXPERT_DIR: %s", GUION_EXPERT_DIR)
    log.info("OPENMONTAGE_DIR:  %s", OPENMONTAGE_DIR)
    log.info("TRINITY_ENABLED:  %s", os.getenv("TRINITY_ENABLED", "false"))
    log.info("=" * 60)

    # ─── Fase 1: Guion Expert (si no viene proyecto pre-hecho) ───────
    if args.idea:
        log.info("[FASE 1] Ejecutando Guion Expert para: %s", args.idea[:80])
        os.chdir(GUION_EXPERT_DIR)
        res = run_full_pipeline(args.idea, auto_detect=True)
        if "error" in res:
            log.error("guion_expert_failed", extra={"error": res["error"]})
            sys.exit(1)
        project_dir = Path(res["output_dir"])
        formato = res.get("formato", "CORTO")
        duracion = res.get("duracion", 1) * 60
        idea_context = args.idea
    else:
        log.info("[FASE 1] Cargando proyecto pre-existente: %s", args.project)
        project_dir = Path(args.project)
        if not project_dir.exists():
            log.error("project_not_found", extra={"path": args.project})
            sys.exit(1)
        idea_context = "Orquestación en base a guion pre-generado."
        formato = "CORTO"
        duracion = 60
        clas = project_dir / "clasificacion" / "result.txt"
        if clas.exists():
            for line in clas.read_text("utf-8").splitlines():
                if "FORMATO" in line.upper():
                    formato = line.split(":")[-1].strip()
                elif "DURACION" in line.upper():
                    m = re.search(r"[\d.]+", line)
                    if m:
                        try:
                            duracion = float(m.group(0)) * 60
                        except ValueError:
                            pass

    # ─── Fase 2: Bridge OpenMontage ──────────────────────────────────
    log.info("[FASE 2] Bridge a OpenMontage (scene_plan.json + stages)")
    paths = export_project_to_openmontage(
        project_dir=project_dir,
        openmontage_root=OPENMONTAGE_DIR,
        idea=idea_context,
        brief_hint={"formato": formato, "duration_seconds": duracion},
    )
    om_project_root = Path(paths["project_root"])
    log.info("bridge_done", extra={"project": str(om_project_root)})

    # ─── Fase 3: Asset Generation (via providers/) ────────────────────
    log.info("[FASE 3] Asset Generation con provider factory")
    scene_plan_path = om_project_root / "stages" / "scene_plan.json"
    assets_dir = om_project_root / "assets"
    summary = run_asset_director(scene_plan_path, assets_dir, formato,
                                 max_workers=args.max_workers)
    if not summary["ok"]:
        log.error("no_scenes_generated")
        sys.exit(1)

    # ─── Fase 4: Edit final ───────────────────────────────────────────
    if args.skip_edit:
        log.info("[FASE 4] --skip-edit activo, salteando concat final.")
    else:
        log.info("[FASE 4] Edit Director (MoviePy concat)")
        final_path = om_project_root / "renders" / "FINAL_CUT.mp4"
        try:
            run_edit_director(scene_plan_path, assets_dir, final_path)
            log.info("PIPELINE COMPLETO — FINAL_CUT: %s", final_path)
        except Exception as e:
            log.error("edit_failed", extra={"error": str(e)})
            sys.exit(1)

    log.info("=" * 60)
    log.info("✅ Pipeline OK. Escenas generadas: %d / fallidas: %d",
             len(summary["ok"]), len(summary["failed"]))
    log.info("Proyecto: %s", om_project_root)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
