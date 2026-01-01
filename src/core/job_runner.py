# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .events import JobStatusEvent, LogEvent, LogLevel, ProgressEvent, StateEvent
from .models import JobSpec, JobState, JobStatus, JobStep
from .dependency_manager import (
    DependencyReporter,
    DependencyStatus,
    DependencyProgress,
    ensure_transcription_dependencies,
)


EmitFn = Callable[[object], None]


class JobRunner:
    """
    Orquesta el pipeline usando las clases existentes pero emitiendo eventos
    UI-agnósticos para que Textual/CLI/GUI puedan observar el progreso.
    """

    def __init__(self, state_manager, emit: EmitFn):
        self.state_manager = state_manager
        self.emit = emit
        self._dependency_ok_cache: set[tuple[str, str, str, str]] = set()

    def run_job(self, job: JobSpec) -> JobStatus:
        status = JobStatus(progress_current=0, progress_total=len(job.video_ids) * max(1, len(job.steps)))
        status.mark_started()
        self.emit(JobStatusEvent(job_id=job.job_id, state=status.state))

        try:
            for video_id in job.video_ids:
                for step in job.steps:
                    status.label = f"{step.value} ({video_id})"
                    self.emit(ProgressEvent(job_id=job.job_id, video_id=video_id, current=status.progress_current, total=status.progress_total, label=status.label))
                    self._run_step(job_id=job.job_id, video_id=video_id, step=step, settings=job.settings)
                    status.progress_current += 1
                    self.emit(ProgressEvent(job_id=job.job_id, video_id=video_id, current=status.progress_current, total=status.progress_total, label=status.label))

            status.mark_finished_ok()
            self.emit(JobStatusEvent(job_id=job.job_id, state=status.state))
            return status

        except Exception as e:
            status.mark_failed(str(e))
            self.emit(LogEvent(job_id=job.job_id, level=LogLevel.ERROR, message=f"Job failed: {e}"))
            self.emit(JobStatusEvent(job_id=job.job_id, state=status.state, error=str(e)))
            return status

    def _run_step(self, *, job_id: str, video_id: str, step: JobStep, settings: Dict[str, Any]) -> None:
        if step == JobStep.TRANSCRIBE:
            self._step_transcribe(job_id=job_id, video_id=video_id, settings=settings.get("transcribe") or {})
        elif step == JobStep.GENERATE_CLIPS:
            self._step_generate_clips(job_id=job_id, video_id=video_id, settings=settings.get("clips") or {})
        elif step == JobStep.EXPORT_CLIPS:
            self._step_export_clips(job_id=job_id, video_id=video_id, settings=settings.get("export") or {})
        elif step == JobStep.EXPORT_SHORTS:
            self._step_export_shorts(job_id=job_id, video_id=video_id, settings=settings)
        elif step == JobStep.DOWNLOAD:
            raise ValueError("DOWNLOAD is not supported as a job step; use Add Videos to download and register.")
        else:
            raise ValueError(f"Unknown job step: {step}")

    def _get_video_path(self, video_id: str) -> str:
        path = self.state_manager.get_video_path(video_id)
        if not path:
            raise FileNotFoundError(f"Video path not registered for: {video_id}")
        return path

    def _step_transcribe(self, *, job_id: str, video_id: str, settings: Dict[str, Any]) -> None:
        self.emit(LogEvent(job_id=job_id, video_id=video_id, level=LogLevel.INFO, message="Starting transcription"))

        video_path = self._get_video_path(video_id)
        if self.state_manager.is_transcribed(video_id) and settings.get("skip_done", True):
            self.emit(LogEvent(job_id=job_id, video_id=video_id, level=LogLevel.INFO, message="Already transcribed; skipping"))
            return

        class _JobDependencyReporter(DependencyReporter):
            def __init__(self, emit: EmitFn, job_id: str, video_id: str):
                self._emit = emit
                self._job_id = job_id
                self._video_id = video_id

            def report(self, event: DependencyProgress) -> None:
                if event.status == DependencyStatus.CHECKING:
                    self._emit(LogEvent(job_id=self._job_id, video_id=self._video_id, level=LogLevel.INFO, message=f"Checking dependency: {event.description}"))
                elif event.status == DependencyStatus.DOWNLOADING:
                    self._emit(LogEvent(job_id=self._job_id, video_id=self._video_id, level=LogLevel.INFO, message=f"Downloading dependency: {event.description}"))
                elif event.status == DependencyStatus.SKIPPED:
                    self._emit(LogEvent(job_id=self._job_id, video_id=self._video_id, level=LogLevel.INFO, message=f"Dependency already installed: {event.description}"))
                elif event.status == DependencyStatus.DONE:
                    self._emit(LogEvent(job_id=self._job_id, video_id=self._video_id, level=LogLevel.INFO, message=f"Dependency ready: {event.description}"))
                elif event.status == DependencyStatus.ERROR:
                    self._emit(LogEvent(job_id=self._job_id, video_id=self._video_id, level=LogLevel.ERROR, message=f"Dependency failed: {event.description} ({event.message})"))

            def is_cancelled(self) -> bool:
                return False

        device_setting = str(settings.get("device", "auto"))
        resolved_device = "cpu" if device_setting == "auto" else device_setting
        model_size = str(settings.get("model", "base"))
        compute_type = str(settings.get("compute_type", "int8"))
        language_code = settings.get("language")
        deps_cache_key = (
            model_size,
            str(language_code) if language_code else "",
            resolved_device,
            compute_type,
        )
        if deps_cache_key not in self._dependency_ok_cache:
            deps_result = ensure_transcription_dependencies(
                model_size=model_size,
                language_code=str(language_code) if language_code else None,
                device=resolved_device,
                compute_type=compute_type,
                reporter=_JobDependencyReporter(self.emit, job_id, video_id),
            )
            if not deps_result.ok:
                details = "; ".join(f"{k}: {v}" for k, v in deps_result.failed.items()) or "Unknown dependency error"
                raise RuntimeError(f"Missing required dependencies: {details}")
            self._dependency_ok_cache.add(deps_cache_key)
        else:
            self.emit(LogEvent(job_id=job_id, video_id=video_id, level=LogLevel.INFO, message="Dependencies already ensured; skipping checks"))

        from src.transcriber import Transcriber

        transcriber = Transcriber(
            model_size=model_size,
            device=device_setting,
            compute_type=compute_type,
        )
        transcript_path = transcriber.transcribe(
            video_path=video_path,
            language=language_code,
            skip_if_exists=settings.get("skip_if_exists", True),
        )
        if not transcript_path:
            raise RuntimeError("Transcription failed (no transcript returned)")

        self.state_manager.mark_transcribed(video_id, transcript_path)
        self.emit(StateEvent(job_id=job_id, video_id=video_id, updates={"transcribed": True, "transcript_path": transcript_path}))
        self.emit(LogEvent(job_id=job_id, video_id=video_id, level=LogLevel.INFO, message="Transcription complete"))

    def _step_generate_clips(self, *, job_id: str, video_id: str, settings: Dict[str, Any]) -> None:
        self.emit(LogEvent(job_id=job_id, video_id=video_id, level=LogLevel.INFO, message="Generating clips"))

        state = self.state_manager.get_video_state(video_id) or {}
        transcript_path = state.get("transcript_path") or state.get("transcription_path")
        if not transcript_path:
            raise RuntimeError("No transcript_path found; run Transcribe first")

        if (state.get("clips_generated") or state.get("clips_metadata_path")) and settings.get("skip_done", True):
            self.emit(LogEvent(job_id=job_id, video_id=video_id, level=LogLevel.INFO, message="Clips already generated; skipping"))
            return

        from src.clips_generator import ClipsGenerator

        generator = ClipsGenerator(
            min_clip_duration=int(settings.get("min_seconds", 30)),
            max_clip_duration=int(settings.get("max_seconds", 90)),
        )
        clips = generator.generate_clips(
            transcript_path=transcript_path,
            min_clips=int(settings.get("min_clips", 3)),
            max_clips=int(settings.get("max_clips", 10)),
        )

        if not clips:
            raise RuntimeError("Clips generation failed (no clips returned)")

        clips_metadata_path = generator.save_clips_metadata(clips=clips, video_id=video_id)

        self.state_manager.mark_clips_generated(video_id, clips or [], clips_metadata_path=clips_metadata_path)
        self.emit(
            StateEvent(
                job_id=job_id,
                video_id=video_id,
                updates={
                    "clips_generated": True,
                    "clips_count": len(clips or []),
                    "clips_metadata_path": clips_metadata_path,
                },
            )
        )
        self.emit(LogEvent(job_id=job_id, video_id=video_id, level=LogLevel.INFO, message="Clips generation complete"))

    def _step_export_clips(self, *, job_id: str, video_id: str, settings: Dict[str, Any]) -> None:
        self.emit(LogEvent(job_id=job_id, video_id=video_id, level=LogLevel.INFO, message="Exporting clips"))

        state = self.state_manager.get_video_state(video_id) or {}
        clips = state.get("clips") or []
        if not clips:
            raise RuntimeError("No clips in state; run Generate Clips first")

        if state.get("clips_exported") and settings.get("skip_done", True):
            self.emit(LogEvent(job_id=job_id, video_id=video_id, level=LogLevel.INFO, message="Clips already exported; skipping"))
            return

        from src.video_exporter import VideoExporter

        exporter = VideoExporter(output_dir=settings.get("output_dir", "output"))
        exported_paths = exporter.export_clips(
            video_path=self._get_video_path(video_id),
            clips=clips,
            aspect_ratio=settings.get("aspect_ratio"),
            video_name=video_id,
            add_subtitles=bool(settings.get("add_subtitles", False)),
            transcript_path=state.get("transcript_path") or state.get("transcription_path"),
            subtitle_style=str(settings.get("subtitle_style", "default")),
            organize_by_style=bool(settings.get("organize_by_style", False)),
            clip_styles=state.get("clip_styles"),
            enable_face_tracking=bool(settings.get("enable_face_tracking", False)),
            face_tracking_strategy=str(settings.get("face_tracking_strategy", "keep_in_frame")),
            face_tracking_sample_rate=int(settings.get("face_tracking_sample_rate", 3)),
            add_logo=bool(settings.get("add_logo", False)),
            logo_path=settings.get("logo_path", "assets/logo.png"),
            logo_position=str(settings.get("logo_position", "top-right")),
            logo_scale=float(settings.get("logo_scale", 0.1)),
        )

        self.state_manager.mark_clips_exported(video_id, exported_paths, aspect_ratio=settings.get("aspect_ratio"))
        self.emit(StateEvent(job_id=job_id, video_id=video_id, updates={"clips_exported": True, "exported_count": len(exported_paths)}))
        self.emit(LogEvent(job_id=job_id, video_id=video_id, level=LogLevel.INFO, message="Export complete"))

    def _step_export_shorts(self, *, job_id: str, video_id: str, settings: Dict[str, Any]) -> None:
        self.emit(LogEvent(job_id=job_id, video_id=video_id, level=LogLevel.INFO, message="Exporting short (full video)"))

        shorts_settings = settings.get("shorts") or {}
        skip_done = bool(shorts_settings.get("skip_done", True))
        if self.state_manager.is_shorts_exported(video_id) and skip_done:
            self.emit(LogEvent(job_id=job_id, video_id=video_id, level=LogLevel.INFO, message="Short already exported; skipping"))
            return

        state = self.state_manager.get_video_state(video_id) or {}

        # Optional: process an already-exported clip instead of the full registered video.
        input_paths = shorts_settings.get("input_paths") or {}
        input_path = None
        if isinstance(input_paths, dict):
            candidate = input_paths.get(video_id)
            if candidate:
                input_path = str(candidate)
        if not input_path:
            input_path = str(shorts_settings.get("input_path") or "").strip() or self._get_video_path(video_id)

        transcript_path = state.get("transcript_path") or state.get("transcription_path")
        if not transcript_path or not self.state_manager.is_transcribed(video_id):
            # Ensure transcription exists (reuses TRANSCRIBE skip behavior).
            self._step_transcribe(job_id=job_id, video_id=video_id, settings=settings.get("transcribe") or {})
            state = self.state_manager.get_video_state(video_id) or {}
            transcript_path = state.get("transcript_path") or state.get("transcription_path")

        if not transcript_path:
            raise RuntimeError("No transcript_path found; run Transcribe first")

        from pathlib import Path

        from src.subtitle_generator import SubtitleGenerator
        from src.video_exporter import VideoExporter

        temp_dir = Path(shorts_settings.get("temp_dir") or (Path("temp") / "shorts"))
        temp_dir.mkdir(parents=True, exist_ok=True)
        srt_path = temp_dir / f"{video_id}.srt"

        srt_generated = SubtitleGenerator().generate_srt_from_transcript(
            transcript_path=str(transcript_path),
            output_path=str(srt_path),
        )
        if not srt_generated:
            raise RuntimeError("Failed to generate SRT from transcript")

        output_dir = shorts_settings.get("output_dir") or str(Path("output") / "shorts")
        exporter = VideoExporter(output_dir=output_dir)
        exported_path = exporter.export_full_video(
            video_path=input_path,
            video_name=video_id,
            output_filename=str(shorts_settings.get("output_filename") or "short.mp4"),
            srt_path=str(srt_path),
            subtitle_style=str(shorts_settings.get("subtitle_style") or "default"),
            add_logo=bool(shorts_settings.get("add_logo", True)),
            logo_path=str(shorts_settings.get("logo_path") or "assets/logo.png"),
            logo_position=str(shorts_settings.get("logo_position") or "top-right"),
            logo_scale=(
                0.1
                if shorts_settings.get("logo_scale") is None
                else float(shorts_settings.get("logo_scale"))
            ),
        )

        self.state_manager.mark_shorts_exported(video_id, exported_path, srt_path=str(srt_path), input_path=input_path)
        self.emit(
            StateEvent(
                job_id=job_id,
                video_id=video_id,
                updates={"shorts_exported": True, "shorts_export_path": exported_path},
            )
        )
        self.emit(LogEvent(job_id=job_id, video_id=video_id, level=LogLevel.INFO, message="Short export complete"))
