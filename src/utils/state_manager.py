"""
State Manager - Guarda el progreso del pipeline para cada video

Este módulo me permite:
- Saber qué videos ya están descargados
- Saber qué videos ya están transcritos
- Saber qué clips ya generé
- Continuar donde me quedé si cierro el programa
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from src.config.settings_schema import (
    get_app_setting_definition,
    validate_and_normalize_app_settings,
)

from .logger import get_logger

logger = get_logger(__name__)


class StateManager:
    """
    Manejo el estado/progreso de todos los videos en el proyecto

    Guardo un archivo JSON con info de cada video:
    {
        "video_id": {
            "filename": "nombre.mp4",
            "downloaded": true,
            "transcribed": false,
            "transcription_path": null,
            "clips_generated": false,
            "clips": [],
            "last_updated": "2025-10-23 22:30:00"
        }
    }
    """

    def __init__(
        self,
        state_file: str = "temp/project_state.json",
        *,
        app_root: Optional[Union[str, Path]] = None,
        settings_file: Optional[Union[str, Path]] = None,
    ):
        # Donde guardo el estado del proyecto
        self.state_file = Path(state_file)

        # Root estable del proyecto (para rutas que no dependen del CWD)
        self.app_root = (
            Path(app_root)
            if app_root is not None
            else Path(__file__).resolve().parents[2]
        )

        # Me aseguro de que la carpeta temp/ exista
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # Cargo el estado actual (o creo uno vacío)
        self.state = self._load_state()

        # Estado de jobs/queue (separado para no romper compatibilidad con project_state.json)
        self.jobs_file = self.state_file.parent / "jobs_state.json"
        self.jobs_state = self._load_jobs_state()

        # Settings globales de la app (persistentes)
        self.settings_file = (
            Path(settings_file)
            if settings_file is not None
            else (self.app_root / "config" / "app_settings.json")
        )
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        loaded_settings = self._load_settings()
        if not isinstance(loaded_settings, dict):
            loaded_settings = {}
        validated, errors = validate_and_normalize_app_settings(loaded_settings)
        self.settings = validated
        if errors:
            for key, msg in errors.items():
                logger.warning(f"Invalid setting {key!r}; reset to default: {msg}")
        if validated != loaded_settings:
            self._save_settings()

    def _load_state(self) -> dict:
        """
        Cargo el estado desde el archivo JSON
        Si no existe, retorno un dict vacío
        """
        if self.state_file.exists():
            try:
                with open(self.state_file, encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                # Si el JSON está corrupto, empiezo de cero
                return {}
        else:
            # Primera vez, archivo no existe
            return {}

    def _load_jobs_state(self) -> dict:
        """
        Cargo estado de jobs desde temp/jobs_state.json.

        Estructura:
        {
          "jobs": { "<job_id>": { "spec": {...}, "status": {...} } },
          "queue": ["<job_id>", ...]
        }
        """
        if self.jobs_file.exists():
            try:
                with open(self.jobs_file, encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        data.setdefault("jobs", {})
                        data.setdefault("queue", [])
                        return data
            except json.JSONDecodeError:
                return {"jobs": {}, "queue": []}
        return {"jobs": {}, "queue": []}

    def _save_jobs_state(self) -> None:
        with open(self.jobs_file, "w", encoding="utf-8") as f:
            json.dump(self.jobs_state, f, indent=2, ensure_ascii=False)

    def _load_settings(self) -> dict:
        """
        Cargo settings globales desde config/app_settings.json.

        Estructura libre, ejemplo:
        {
          "logo_path": "assets/logo.png"
        }
        """
        if self.settings_file.exists():
            try:
                with open(self.settings_file, encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_settings(self) -> None:
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(
                f"No se pudieron guardar settings en {self.settings_file}: {e}"
            )

    def get_setting(self, key: str, default=None):
        if default is None:
            definition = get_app_setting_definition(key)
            if definition is not None:
                default = definition.default
        return (self.settings or {}).get(key, default)

    def set_setting(self, key: str, value) -> None:
        if self.settings is None:
            self.settings = {}
        definition = get_app_setting_definition(key)
        if definition is not None:
            self.settings[key] = definition.validate_and_normalize(value)
        else:
            self.settings[key] = value
        self._save_settings()

    def is_first_run(self) -> bool:
        """Check if this is the first run (wizard not completed)."""
        return not self.get_setting("_wizard_completed", False)

    def mark_wizard_completed(self) -> None:
        """Mark the setup wizard as completed."""
        self.set_setting("_wizard_completed", True)

    def load_settings(self) -> dict:
        """Return the current settings dict."""
        return dict(self.settings or {})

    def _save_state(self):
        """
        Guardo el estado actual al archivo JSON
        """
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def register_video(
        self,
        video_id: str,
        filename: str,
        video_path: Optional[str] = None,
        content_type: str = "tutorial",
        preset: Optional[dict] = None,
    ) -> None:
        """
        Registro un nuevo video en el sistema

        Args:
            video_id: ID único del video
            filename: Nombre del archivo
            video_path: Ruta al archivo de video (absoluta o relativa)
            content_type: Tipo de contenido (podcast, tutorial, livestream, etc.)
            preset: Preset de configuración completo
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if video_id not in self.state:
            self.state[video_id] = {
                "filename": filename,
                "video_path": self._normalize_path(video_path),
                "downloaded": True,
                "transcribed": False,
                "transcription_path": None,
                "transcript_path": None,  # Alias para compatibilidad
                "clips_generated": False,
                "clips": [],
                "clips_metadata_path": None,
                # Shorts-only processing (additive; does not couple to clips_* flags)
                "shorts_exported": False,
                "shorts_export_path": None,
                "shorts_srt_path": None,
                "shorts_input_path": None,
                # Auto-naming feature
                "auto_generated_name": None,
                "content_type": content_type,  # Nuevo: tipo de contenido
                "preset": preset if preset else {},  # Nuevo: configuración
                "last_updated": now,
            }
            self._save_state()
            return

        # Si ya existe, solo actualizo metadata sin resetear progreso
        updated = False
        existing = self.state[video_id]

        if filename and existing.get("filename") != filename:
            existing["filename"] = filename
            updated = True

        if video_path:
            existing_path = existing.get("video_path")
            normalized = self._normalize_path(video_path)
            if existing_path != normalized:
                existing["video_path"] = normalized
                updated = True

        if content_type and existing.get("content_type") != content_type:
            existing["content_type"] = content_type
            updated = True

        if preset:
            existing["preset"] = preset
            updated = True

        if updated:
            existing["last_updated"] = now
            self._save_state()

    def get_video_path(self, video_id: str) -> Optional[str]:
        """
        Obtengo la ruta al archivo de video (si está registrada)
        """
        state = self.get_video_state(video_id)
        if not state:
            return None
        return state.get("video_path")

    def _normalize_path(self, path: Optional[str]) -> Optional[str]:
        if not path:
            return None
        return str(Path(path))

    def mark_transcribed(self, video_id: str, transcription_path: str) -> None:
        """
        Marco un video como transcrito y guardo la ruta del archivo de transcripción
        """
        if video_id in self.state:
            self.state[video_id]["transcribed"] = True
            normalized = self._normalize_path(transcription_path)
            self.state[video_id]["transcription_path"] = normalized
            self.state[video_id]["transcript_path"] = normalized  # Alias
            self.state[video_id]["last_updated"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            self._save_state()

    def mark_clips_generated(
        self,
        video_id: str,
        clips: list[dict],
        clips_metadata_path: Optional[str] = None,
    ) -> None:
        """
        Marco que ya generé clips para este video

        Args:
            video_id: ID del video
            clips: Lista de dicts con info de cada clip
            clips_metadata_path: Ruta al JSON con metadata de clips
        """
        if video_id in self.state:
            self.state[video_id]["clips_generated"] = True
            self.state[video_id]["clips"] = clips
            self.state[video_id]["clips_metadata_path"] = self._normalize_path(
                clips_metadata_path
            )
            self.state[video_id]["last_updated"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            self._save_state()

    def mark_clips_exported(
        self,
        video_id: str,
        exported_paths: list[str],
        aspect_ratio: Optional[str] = None,
    ) -> None:
        """
        Marco que ya exporté los clips a archivos de video

        Args:
            video_id: ID del video
            exported_paths: Lista de rutas a los clips exportados
            aspect_ratio: Aspect ratio usado (9:16, 1:1, etc.)
        """
        if video_id in self.state:
            self.state[video_id]["clips_exported"] = True
            self.state[video_id]["exported_clips"] = [
                self._normalize_path(p) for p in (exported_paths or []) if p
            ]
            self.state[video_id]["export_aspect_ratio"] = aspect_ratio
            self.state[video_id]["last_updated"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            self._save_state()

    def mark_shorts_exported(
        self,
        video_id: str,
        exported_path: str,
        *,
        srt_path: Optional[str] = None,
        input_path: Optional[str] = None,
    ) -> None:
        """
        Marco que ya exporté el short (video completo) con subtítulos/logo.
        """
        if video_id in self.state:
            self.state[video_id]["shorts_exported"] = True
            self.state[video_id]["shorts_export_path"] = exported_path
            self.state[video_id]["shorts_srt_path"] = srt_path
            self.state[video_id]["shorts_input_path"] = input_path
            self.state[video_id]["last_updated"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            self._save_state()

    def set_auto_generated_name(self, video_id: str, name: str) -> None:
        """
        Guarda el nombre auto-generado para un video.
        """
        if video_id in self.state:
            self.state[video_id]["auto_generated_name"] = name
            self.state[video_id]["last_updated"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            self._save_state()

    def get_auto_generated_name(self, video_id: str) -> Optional[str]:
        """
        Obtiene el nombre auto-generado de un video.
        """
        state = self.get_video_state(video_id)
        return state.get("auto_generated_name") if state else None

    def get_video_state(self, video_id: str) -> Optional[dict]:
        """
        Obtengo el estado de un video específico
        Retorno None si el video no está registrado
        """
        return self.state.get(video_id)

    def get_all_videos(self) -> dict:
        """
        Obtengo todos los videos registrados
        """
        return self.state

    def is_transcribed(self, video_id: str) -> bool:
        """
        Verifico si un video ya está transcrito
        """
        video_state = self.get_video_state(video_id)
        if video_state:
            return video_state.get("transcribed", False)
        return False

    def is_shorts_exported(self, video_id: str) -> bool:
        video_state = self.get_video_state(video_id)
        if video_state:
            return bool(video_state.get("shorts_exported", False))
        return False

    def get_next_step(self, video_id: str) -> str:
        """
        Determino cuál es el siguiente paso para este video

        Retorno: "transcribe", "generate_clips", "export", "done"
        """
        video_state = self.get_video_state(video_id)

        if not video_state:
            return "unknown"

        if not video_state["transcribed"]:
            return "transcribe"
        elif not video_state["clips_generated"]:
            return "generate_clips"
        elif not video_state.get("clips_exported", False):
            return "export"
        else:
            return "done"

    def clear_video_state(self, video_id: str) -> None:
        """
        Elimino el estado de un video (útil si borro el video)
        """
        if video_id in self.state:
            del self.state[video_id]
            self._save_state()

    def reset_video_stages(self, video_id: str, stages: list[str]) -> None:
        """
        Resetea etapas específicas de un video para permitir re-procesamiento.

        Args:
            video_id: ID del video
            stages: Lista de etapas a resetear: "transcription", "clips", "export", "shorts"
        """
        if video_id not in self.state:
            return

        video = self.state[video_id]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if "transcription" in stages:
            video["transcribed"] = False
            video["transcription_path"] = None
            video["transcript_path"] = None
            # Si reseteamos transcripción, también debemos resetear stages dependientes
            stages = list(set(stages) | {"clips", "export", "shorts"})

        if "clips" in stages:
            video["clips_generated"] = False
            video["clips"] = []
            video["clips_metadata_path"] = None
            # Si reseteamos clips, también reseteamos export
            if "export" not in stages:
                stages = list(set(stages) | {"export"})

        if "export" in stages:
            video["clips_exported"] = False
            video["exported_clips"] = []

        if "shorts" in stages:
            video["shorts_exported"] = False
            video["shorts_export_path"] = None
            video["shorts_srt_path"] = None
            video["shorts_input_path"] = None

        video["last_updated"] = now
        self._save_state()

    # ---------------------------
    # Jobs / Queue (additive API)
    # ---------------------------

    def create_job_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def enqueue_job(self, job_spec: dict, initial_status: Optional[dict] = None) -> str:
        """
        Encola un job para ejecución.

        Args:
            job_spec: Dict serializable (p.ej. JobSpec.to_dict())
            initial_status: Dict serializable (p.ej. JobStatus.to_dict())
        """
        job_id = str(job_spec.get("job_id") or self.create_job_id())
        job_spec = dict(job_spec)
        job_spec["job_id"] = job_id

        if initial_status is None:
            initial_status = {"state": "pending"}

        self.jobs_state.setdefault("jobs", {})[job_id] = {
            "spec": job_spec,
            "status": dict(initial_status),
        }
        queue = self.jobs_state.setdefault("queue", [])
        if job_id not in queue:
            queue.append(job_id)
        self._save_jobs_state()
        return job_id

    def list_jobs(self) -> dict[str, dict]:
        return dict(self.jobs_state.get("jobs") or {})

    def get_job(self, job_id: str) -> Optional[dict]:
        return (self.jobs_state.get("jobs") or {}).get(job_id)

    def get_job_spec(self, job_id: str) -> Optional[dict]:
        job = self.get_job(job_id)
        return job.get("spec") if job else None

    def get_job_status(self, job_id: str) -> Optional[dict]:
        job = self.get_job(job_id)
        return job.get("status") if job else None

    def update_job_status(self, job_id: str, updates: dict) -> None:
        job = self.get_job(job_id)
        if not job:
            return
        status = job.setdefault("status", {})
        status.update(dict(updates))
        job["status"] = status
        self.jobs_state["jobs"][job_id] = job
        self._save_jobs_state()

    def dequeue_next_job_id(self) -> Optional[str]:
        queue = self.jobs_state.get("queue") or []
        if not queue:
            return None
        job_id = queue.pop(0)
        self.jobs_state["queue"] = queue
        self._save_jobs_state()
        return job_id

    def remove_job(self, job_id: str) -> None:
        jobs = self.jobs_state.get("jobs") or {}
        jobs.pop(job_id, None)
        self.jobs_state["jobs"] = jobs
        self.jobs_state["queue"] = [
            j for j in (self.jobs_state.get("queue") or []) if j != job_id
        ]
        self._save_jobs_state()


# Función helper para obtener el state manager global
_state_manager_instance = None
_state_manager_init_kwargs: dict[str, object] = {}


def get_state_manager() -> StateManager:
    """
    Obtengo la instancia global del StateManager
    Patrón Singleton - solo una instancia en todo el programa
    """
    global _state_manager_instance
    if _state_manager_instance is None:
        _state_manager_instance = StateManager(**(_state_manager_init_kwargs or {}))
    return _state_manager_instance
