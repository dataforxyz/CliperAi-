from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".mkv", ".webm"}


def is_supported_video_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS


def _short_hash(text: str, length: int = 8) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length]


def compute_unique_video_id(video_path: Path, state_manager) -> str:
    """
    Mantiene compatibilidad con IDs viejos (stem) y evita colisiones cuando se
    agregan archivos con el mismo nombre desde rutas distintas.
    """
    base = video_path.stem
    existing = state_manager.get_video_state(base)
    if not existing:
        return base

    existing_path = (existing.get("video_path") or "").strip()
    if existing_path:
        try:
            if Path(existing_path).resolve() == video_path.resolve():
                return base
        except Exception:
            pass

    try:
        resolved = str(video_path.resolve())
    except Exception:
        resolved = str(video_path)
    return f"{base}_{_short_hash(resolved)}"


def discover_downloads_and_register(
    state_manager,
    downloads_dir: Path = Path("downloads"),
) -> list[Path]:
    """
    Descubre videos en downloads/ y los registra/actualiza en el state.
    Retorna la lista de archivos encontrados (únicos).
    """
    downloads_dir.mkdir(parents=True, exist_ok=True)

    video_files: set[Path] = set()
    for ext in SUPPORTED_VIDEO_EXTENSIONS:
        video_files |= set(downloads_dir.glob(f"*{ext}"))
        video_files |= set(downloads_dir.glob(f"*{ext.upper()}"))

    for video_file in video_files:
        video_id = compute_unique_video_id(video_file, state_manager)
        state_manager.register_video(
            video_id=video_id,
            filename=video_file.name,
            video_path=str(video_file),
        )

    return sorted(video_files, key=lambda p: p.name.lower())


def _resolve_existing_video_path(
    video_id: str, filename: str, video_path: str | None
) -> Path | None:
    if video_path:
        candidate = Path(video_path)
        if candidate.exists() and candidate.is_file():
            return candidate

    fallback = Path("downloads") / filename
    if fallback.exists() and fallback.is_file():
        return fallback

    return None


def load_registered_videos(state_manager) -> list[dict[str, str]]:
    """
    Fuente única de verdad para el UI:
    - Descubre videos en downloads/ y los registra/actualiza en el state.
    - Incluye videos registrados con ruta fuera del proyecto.
    - Solo retorna videos cuyo archivo existe actualmente.

    Returns:
        List[{"filename": str, "path": str, "video_id": str}]
    """
    discover_downloads_and_register(state_manager)

    videos: list[dict[str, str]] = []
    for video_id, state in state_manager.get_all_videos().items():
        filename = state.get("filename") or f"{video_id}.mp4"
        resolved_path = _resolve_existing_video_path(
            video_id, filename, state.get("video_path")
        )
        if not resolved_path:
            continue

        if not state.get("video_path"):
            state_manager.register_video(
                video_id=video_id, filename=filename, video_path=str(resolved_path)
            )

        videos.append(
            {"filename": filename, "path": str(resolved_path), "video_id": video_id}
        )

    videos.sort(key=lambda v: v["filename"].lower())
    return videos


def collect_local_video_paths(
    input_str: str, *, recursive: bool = False
) -> tuple[list[Path], list[str]]:
    """
    Accepts:
    - A file path
    - A folder path (adds supported video files inside)
    - Multiple paths separated by commas
    """
    raw = (input_str or "").strip()
    if not raw:
        return [], ["No input provided"]

    parts = [p.strip() for p in raw.split(",") if p.strip()]
    paths: list[Path] = []
    errors: list[str] = []
    for part in parts:
        normalized = part.strip().strip('"').strip("'")
        p = Path(normalized).expanduser()
        if not p.exists():
            errors.append(f"Path not found: {part}")
            continue
        paths.append(p)

    filtered: list[Path] = []
    for p in paths:
        if p.is_dir():
            iterator = p.rglob("*") if recursive else p.iterdir()
            found_any = False
            for child in iterator:
                if is_supported_video_file(child):
                    filtered.append(child)
                    found_any = True
            if not found_any:
                errors.append(f"No supported videos found in folder: {p}")
        elif is_supported_video_file(p):
            filtered.append(p)
        else:
            errors.append(f"Unsupported video file: {p}")

    unique: list[Path] = []
    seen: set[str] = set()
    for p in filtered:
        try:
            key = str(p.resolve())
        except Exception:
            key = str(p)
        if key not in seen:
            seen.add(key)
            unique.append(p)

    return unique, errors


def register_local_videos(
    state_manager,
    paths: Iterable[Path],
    *,
    content_type: str = "tutorial",
    preset: dict | None = None,
) -> list[str]:
    """
    Registra paths locales en el state y retorna la lista de video_ids creados.
    """
    video_ids: list[str] = []
    for p in paths:
        video_file = Path(p)
        if not is_supported_video_file(video_file):
            continue
        video_id = compute_unique_video_id(video_file, state_manager)
        state_manager.register_video(
            video_id=video_id,
            filename=video_file.name,
            video_path=str(video_file),
            content_type=content_type,
            preset=preset or {},
        )
        video_ids.append(video_id)
    return video_ids
