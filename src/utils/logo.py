from __future__ import annotations

from pathlib import Path

DEFAULT_BUILTIN_LOGO_PATH = "assets/logo.png"
_ALLOWED_LOGO_SUFFIXES = {".png", ".jpg", ".jpeg"}


def _is_allowed_logo_file(path: Path) -> bool:
    return path.suffix.lower() in _ALLOWED_LOGO_SUFFIXES


def _looks_like_png(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return f.read(8) == b"\x89PNG\r\n\x1a\n"
    except OSError:
        return False


def _looks_like_jpeg(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            return f.read(3) == b"\xff\xd8\xff"
    except OSError:
        return False


def _has_expected_image_signature(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return _looks_like_png(path)
    if suffix in {".jpg", ".jpeg"}:
        return _looks_like_jpeg(path)
    return False


def _get_app_root() -> Path:
    # src/utils/logo.py -> <repo_root>/src/utils/logo.py
    return Path(__file__).resolve().parents[2]


def _get_builtin_logo_file() -> Path:
    return (_get_app_root() / DEFAULT_BUILTIN_LOGO_PATH).resolve()


def _coerce_to_existing_logo_file(candidate: str | None) -> Path | None:
    if not candidate:
        return None

    candidate_str = str(candidate)

    # Treat "assets/..." as a logical path anchored at the app root (not CWD).
    if candidate_str.startswith("assets/"):
        anchored = _get_app_root() / candidate_str
        if (
            anchored.exists()
            and anchored.is_file()
            and _is_allowed_logo_file(anchored)
            and _has_expected_image_signature(anchored)
        ):
            return anchored.resolve()
        return None

    path = Path(candidate_str).expanduser()

    if path.exists() and path.is_file():
        if not _is_allowed_logo_file(path):
            return None
        if not _has_expected_image_signature(path):
            return None
        return path.resolve()

    return None


def resolve_logo_path(
    *,
    user_logo_path: str | None = None,
    saved_logo_path: str | None = None,
    builtin_logo_path: str = DEFAULT_BUILTIN_LOGO_PATH,
) -> str | None:
    """
    Resuelve una ruta de logo válida, con fallback seguro.

    Prioridad:
    1) user_logo_path (override por export)
    2) saved_logo_path (default persistido)
    3) builtin_logo_path (assets/logo.png)
    """
    for candidate in (user_logo_path, saved_logo_path):
        resolved = _coerce_to_existing_logo_file(candidate)
        if resolved:
            return str(resolved)

    # El builtin se resuelve de forma determinista respecto al app root:
    # - "assets/..." ya está anclado por _coerce_to_existing_logo_file()
    # - cualquier ruta relativa se ancla a app root para no depender del CWD
    builtin_candidate = builtin_logo_path
    if builtin_candidate and not str(builtin_candidate).startswith("assets/"):
        builtin_path = Path(str(builtin_candidate)).expanduser()
        if not builtin_path.is_absolute():
            builtin_candidate = str(_get_app_root() / builtin_path)

    resolved = _coerce_to_existing_logo_file(builtin_candidate)
    if resolved:
        return str(resolved)
    return None


def is_valid_logo_location(location: str | None) -> bool:
    return _coerce_to_existing_logo_file(location) is not None


def coerce_logo_file(location: str | None) -> str | None:
    """
    Convierte una ubicación (archivo) a un path de archivo existente.
    No aplica fallback: si es inválido, retorna None.
    """
    resolved = _coerce_to_existing_logo_file(location)
    return str(resolved) if resolved else None


def normalize_logo_setting_value(location: str) -> str:
    """
    Normaliza el valor a guardar en settings.

    - Mantiene rutas a assets como relativas para que el repo sea portable.
    - Para rutas custom, guarda una ruta absoluta expandida/resuelta.
    """
    if location.startswith("assets/") or location == DEFAULT_BUILTIN_LOGO_PATH:
        return location

    path = Path(location).expanduser()
    try:
        resolved = path.resolve()
        if resolved == _get_builtin_logo_file():
            return DEFAULT_BUILTIN_LOGO_PATH
        return str(resolved)
    except Exception:
        return str(path)


def list_logo_candidates(
    *,
    saved_logo_path: str | None = None,
    builtin_logo_path: str = DEFAULT_BUILTIN_LOGO_PATH,
    logos_dir: str = "assets/logos",
) -> list[dict[str, str]]:
    """
    List valid logo options for selection UIs.

    Returns a de-duplicated list of dicts:
      - name: human-friendly label
      - setting_value: value suitable for job/settings ("assets/..." or absolute path)
      - resolved_path: absolute resolved path to the image file

    Scans:
      1. Built-in logo (assets/logo.png)
      2. Saved logo path from settings (if valid)
      3. All logo files in assets/logos/ directory
    """
    resolved_seen: set[str] = set()
    options: list[dict[str, str]] = []

    def _add(label: str, candidate: str | None) -> None:
        if not candidate:
            return
        resolved = _coerce_to_existing_logo_file(candidate)
        if not resolved:
            return
        resolved_str = str(resolved)
        if resolved_str in resolved_seen:
            return
        resolved_seen.add(resolved_str)

        setting_value = normalize_logo_setting_value(candidate)
        options.append(
            {
                "name": label,
                "setting_value": setting_value,
                "resolved_path": resolved_str,
            }
        )

    # Built-in first so it stays stable as a default option.
    _add("Built-in", builtin_logo_path)

    if saved_logo_path:
        saved_name = Path(str(saved_logo_path)).expanduser().name or "Saved"
        _add(f"Saved ({saved_name})", saved_logo_path)

    # Scan logos directory for additional options
    logos_path = _get_app_root() / logos_dir
    if logos_path.is_dir():
        for logo_file in sorted(logos_path.iterdir()):
            if logo_file.is_file() and _is_allowed_logo_file(logo_file):
                # Use relative path for portability
                relative_path = f"{logos_dir}/{logo_file.name}"
                label = logo_file.stem.replace("_", " ").replace("-", " ").title()
                _add(label, relative_path)

    return options
