from __future__ import annotations

import gc
import os
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Callable, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence


class EnsureDecision(str, Enum):
    RETRY = "retry"
    SKIP = "skip"
    CANCEL = "cancel"


class DependencyStatus(str, Enum):
    CHECKING = "checking"
    DOWNLOADING = "downloading"
    SKIPPED = "skipped"
    DONE = "done"
    ERROR = "error"


@dataclass(frozen=True)
class DependencyProgress:
    key: str
    description: str
    status: DependencyStatus
    index: int
    total: int
    message: str = ""
    attempt: int = 1


class DependencyReporter(Protocol):
    def report(self, event: DependencyProgress) -> None: ...

    def is_cancelled(self) -> bool: ...


class NullDependencyReporter:
    def report(self, event: DependencyProgress) -> None:
        return

    def is_cancelled(self) -> bool:
        return False


CheckFn = Callable[[], bool]
EnsureFn = Callable[[], None]
OnErrorFn = Callable[[DependencyProgress, BaseException], EnsureDecision]


@dataclass(frozen=True)
class DependencySpec:
    key: str
    description: str
    check: CheckFn
    ensure: EnsureFn


@dataclass(frozen=True)
class EnsureResult:
    completed: list[str]
    skipped: list[str]
    failed: dict[str, str]
    canceled: bool

    @property
    def ok(self) -> bool:
        return (not self.canceled) and (not self.failed)


def _parse_csv_env(name: str, default: str) -> list[str]:
    raw = os.environ.get(name, default)
    parts = [p.strip() for p in raw.split(",")]
    return [p for p in parts if p]


def _guess_faster_whisper_repo_id(model_size: str) -> str | None:
    # WhisperX uses faster-whisper under the hood; these are the canonical HF repos.
    # If WhisperX changes its defaults, we fall back to `whisperx.load_model(...)`.
    mapping = {
        "tiny": "Systran/faster-whisper-tiny",
        "base": "Systran/faster-whisper-base",
        "small": "Systran/faster-whisper-small",
        "medium": "Systran/faster-whisper-medium",
        "large-v1": "Systran/faster-whisper-large-v1",
        "large-v2": "Systran/faster-whisper-large-v2",
        "large-v3": "Systran/faster-whisper-large-v3",
    }
    return mapping.get(model_size)


def _hf_snapshot_cached(repo_id: str) -> bool:
    try:
        from huggingface_hub import snapshot_download
    except Exception:
        return False

    try:
        snapshot_download(repo_id=repo_id, local_files_only=True)
        return True
    except Exception:
        return False


def _hf_snapshot_download(repo_id: str) -> None:
    from huggingface_hub import snapshot_download

    snapshot_download(repo_id=repo_id)


def _dependency_markers_dir() -> str:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(
        os.path.expanduser("~"), ".cache"
    )
    return os.path.join(base, "cliper", "dependency_markers")


def _dependency_marker_path(key: str) -> str:
    safe = "".join(c if c.isalnum() or c in {"-", "_", ":"} else "_" for c in key)
    return os.path.join(_dependency_markers_dir(), f"{safe}.ok")


def is_dependency_marked_installed(key: str) -> bool:
    return os.path.exists(_dependency_marker_path(key))


def mark_dependency_installed(key: str) -> None:
    path = _dependency_marker_path(key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("ok\n")
    except Exception:
        # Marker is a best-effort optimization; ensure path may still be cached by HF/WhisperX.
        return


_WHISPER_MODEL_CACHE: dict[tuple[str, str, str], object] = {}
_ALIGN_MODEL_CACHE: dict[tuple[str, str], tuple[object, object]] = {}
_ENSURED_IN_PROCESS: set[str] = set()


def build_required_dependencies(
    *,
    whisper_model_size: str = "base",
    align_language_codes: Sequence[str] | None = None,
    whisper_device: str = "cpu",
    whisper_compute_type: str = "int8",
) -> list[DependencySpec]:
    if align_language_codes is None:
        align_language_codes = _parse_csv_env("CLIPER_PREFETCH_ALIGN_LANGS", "en,es")

    specs: list[DependencySpec] = []
    whisper_key = f"whisper_model:{whisper_model_size}"
    specs.append(
        DependencySpec(
            key=whisper_key,
            description=f"Whisper model ({whisper_model_size})",
            check=lambda key=whisper_key: is_dependency_marked_installed(key)
            or is_whisper_model_cached(model_size=whisper_model_size),
            ensure=lambda: prefetch_whisper_model(
                model_size=whisper_model_size,
                device=whisper_device,
                compute_type=whisper_compute_type,
            ),
        )
    )

    for lang in align_language_codes:
        align_key = f"align_model:{lang}"
        specs.append(
            DependencySpec(
                key=align_key,
                description=f"Alignment model ({lang})",
                check=lambda lang=lang, key=align_key: is_dependency_marked_installed(
                    key
                )
                or is_align_model_cached(language_code=lang),
                ensure=lambda lang=lang: prefetch_align_model(
                    language_code=lang, device=whisper_device
                ),
            )
        )

    return specs


def ensure_all_required(
    specs: Sequence[DependencySpec],
    *,
    reporter: DependencyReporter | None = None,
    on_error: OnErrorFn | None = None,
    max_attempts: int = 2,
) -> EnsureResult:
    reporter = reporter or NullDependencyReporter()

    completed: list[str] = []
    skipped: list[str] = []
    failed: dict[str, str] = {}

    total = len(specs)
    for idx, spec in enumerate(specs, start=1):
        if reporter.is_cancelled():
            return EnsureResult(
                completed=completed, skipped=skipped, failed=failed, canceled=True
            )

        if spec.key in _ENSURED_IN_PROCESS:
            skipped.append(spec.key)
            reporter.report(
                DependencyProgress(
                    key=spec.key,
                    description=spec.description,
                    status=DependencyStatus.SKIPPED,
                    index=idx,
                    total=total,
                    message="Already ensured this run",
                )
            )
            continue

        reporter.report(
            DependencyProgress(
                key=spec.key,
                description=spec.description,
                status=DependencyStatus.CHECKING,
                index=idx,
                total=total,
            )
        )
        present = spec.check()
        if present:
            skipped.append(spec.key)
            _ENSURED_IN_PROCESS.add(spec.key)
            mark_dependency_installed(spec.key)
            reporter.report(
                DependencyProgress(
                    key=spec.key,
                    description=spec.description,
                    status=DependencyStatus.SKIPPED,
                    index=idx,
                    total=total,
                    message="Already installed",
                )
            )
            continue

        attempt = 0
        while True:
            attempt += 1
            if reporter.is_cancelled():
                return EnsureResult(
                    completed=completed, skipped=skipped, failed=failed, canceled=True
                )

            reporter.report(
                DependencyProgress(
                    key=spec.key,
                    description=spec.description,
                    status=DependencyStatus.DOWNLOADING,
                    index=idx,
                    total=total,
                    attempt=attempt,
                )
            )
            try:
                spec.ensure()
                completed.append(spec.key)
                _ENSURED_IN_PROCESS.add(spec.key)
                mark_dependency_installed(spec.key)
                reporter.report(
                    DependencyProgress(
                        key=spec.key,
                        description=spec.description,
                        status=DependencyStatus.DONE,
                        index=idx,
                        total=total,
                        attempt=attempt,
                    )
                )
                break
            except Exception as e:
                reporter.report(
                    DependencyProgress(
                        key=spec.key,
                        description=spec.description,
                        status=DependencyStatus.ERROR,
                        index=idx,
                        total=total,
                        message=str(e),
                        attempt=attempt,
                    )
                )

                if attempt >= max_attempts:
                    failed[spec.key] = str(e)
                    break

                decision = EnsureDecision.CANCEL
                if on_error is not None:
                    decision = on_error(
                        DependencyProgress(
                            key=spec.key,
                            description=spec.description,
                            status=DependencyStatus.ERROR,
                            index=idx,
                            total=total,
                            message=str(e),
                            attempt=attempt,
                        ),
                        e,
                    )
                else:
                    decision = EnsureDecision.CANCEL

                if decision == EnsureDecision.RETRY:
                    continue
                if decision == EnsureDecision.SKIP:
                    failed[spec.key] = str(e)
                    break
                return EnsureResult(
                    completed=completed, skipped=skipped, failed=failed, canceled=True
                )

    return EnsureResult(
        completed=completed, skipped=skipped, failed=failed, canceled=False
    )


def ensure_transcription_dependencies(
    *,
    model_size: str,
    language_code: str | None = None,
    device: str = "cpu",
    compute_type: str = "int8",
    reporter: DependencyReporter | None = None,
) -> EnsureResult:
    langs: list[str] = []
    if language_code:
        langs = [language_code]

    specs = build_required_dependencies(
        whisper_model_size=model_size,
        align_language_codes=langs or None,
        whisper_device=device,
        whisper_compute_type=compute_type,
    )
    return ensure_all_required(specs, reporter=reporter, max_attempts=1)


def is_whisper_model_cached(*, model_size: str) -> bool:
    repo_id = _guess_faster_whisper_repo_id(model_size)
    if not repo_id:
        return False
    return _hf_snapshot_cached(repo_id)


def prefetch_whisper_model(*, model_size: str, device: str, compute_type: str) -> None:
    repo_id = _guess_faster_whisper_repo_id(model_size)
    if repo_id:
        try:
            _hf_snapshot_download(repo_id)
            return
        except Exception:
            # Fall back to WhisperX's own download mechanism.
            pass

    model = load_whisper_model(
        model_size=model_size,
        device=device,
        compute_type=compute_type,
        cache_in_memory=False,
    )
    del model
    gc.collect()


def load_whisper_model(
    *,
    model_size: str,
    device: str,
    compute_type: str,
    cache_in_memory: bool = True,
) -> object:
    cache_key = (model_size, device, compute_type)
    if cache_in_memory and cache_key in _WHISPER_MODEL_CACHE:
        return _WHISPER_MODEL_CACHE[cache_key]

    try:
        import whisperx  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "WhisperX is not installed; install project dependencies to download models."
        ) from e

    model = whisperx.load_model(model_size, device, compute_type=compute_type)
    if cache_in_memory:
        _WHISPER_MODEL_CACHE[cache_key] = model
    return model


def _resolve_align_repo_id(language_code: str) -> str | None:
    try:
        from whisperx.alignment import DEFAULT_ALIGN_MODELS  # type: ignore
    except Exception:
        return None

    if language_code in DEFAULT_ALIGN_MODELS:
        return str(DEFAULT_ALIGN_MODELS[language_code])
    base = language_code.split("-")[0]
    if base in DEFAULT_ALIGN_MODELS:
        return str(DEFAULT_ALIGN_MODELS[base])
    return None


def is_align_model_cached(*, language_code: str) -> bool:
    repo_id = _resolve_align_repo_id(language_code)
    if not repo_id:
        return False
    return _hf_snapshot_cached(repo_id)


def prefetch_align_model(*, language_code: str, device: str) -> None:
    repo_id = _resolve_align_repo_id(language_code)
    if repo_id:
        try:
            _hf_snapshot_download(repo_id)
            return
        except Exception:
            pass

    model_a, metadata = load_align_model(
        language_code=language_code, device=device, cache_in_memory=False
    )
    del model_a
    del metadata
    gc.collect()


def load_align_model(
    *,
    language_code: str,
    device: str,
    cache_in_memory: bool = True,
) -> tuple[object, object]:
    cache_key = (language_code, device)
    if cache_in_memory and cache_key in _ALIGN_MODEL_CACHE:
        return _ALIGN_MODEL_CACHE[cache_key]

    try:
        import whisperx  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "WhisperX is not installed; install project dependencies to download alignment models."
        ) from e

    model_a, metadata = whisperx.load_align_model(
        language_code=language_code, device=device
    )
    if cache_in_memory:
        _ALIGN_MODEL_CACHE[cache_key] = (model_a, metadata)
    return model_a, metadata
