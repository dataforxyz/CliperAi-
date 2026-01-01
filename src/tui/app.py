# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, DataTable, Footer, Header, Input, RichLog, Static

from src.utils import get_state_manager
from src.utils.video_registry import load_registered_videos
from src.utils.video_registry import collect_local_video_paths, register_local_videos

from src.core.events import JobStatusEvent, LogEvent, ProgressEvent, StateEvent
from src.core.job_runner import JobRunner
from src.core.models import JobSpec, JobState, JobStep


class AddVideosModal(ModalScreen[Optional[Dict[str, object]]]):
    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
    ]

    def on_mount(self) -> None:
        # Default focus so tests and users can type immediately.
        self.query_one("#paths", Input).focus()

    def compose(self) -> ComposeResult:
        yield Static("Add Videos", id="title")
        yield Static("YouTube URL:", classes="label")
        yield Input(placeholder="https://youtube.com/watch?v=…", id="youtube_url")
        yield Static("Local file(s) or folder path(s):", classes="label")
        yield Input(placeholder="/path/to/video.mp4, /path/to/folder", id="paths")
        yield Checkbox("Include subfolders (for folders)", id="recursive", value=False)
        with Horizontal(classes="buttons"):
            yield Button("Add", id="add", variant="primary")
            yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        if event.button.id == "add":
            url = (self.query_one("#youtube_url", Input).value or "").strip()
            paths = (self.query_one("#paths", Input).value or "").strip()
            recursive = bool(self.query_one("#recursive", Checkbox).value)
            self.dismiss({"url": url, "paths": paths, "recursive": recursive})


class ProcessShortsModal(ModalScreen[Optional[Dict[str, object]]]):
    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
    ]

    def __init__(self, *, title: str, choices: List[str]):
        super().__init__()
        self._title = title
        self._choices = choices
        self._choice_key_to_path: Dict[str, str] = {}

    def on_mount(self) -> None:
        table = self.query_one("#choices", DataTable)
        table.cursor_type = "row"
        table.focus()

    def compose(self) -> ComposeResult:
        yield Static(self._title, id="title")
        yield Static("Input to process as a short:", classes="label")
        table = DataTable(id="choices")
        table.add_columns("Source")
        table.add_row("Full video", key="__full__")
        self._choice_key_to_path.clear()
        for idx, path in enumerate(self._choices):
            key = f"__choice_{idx}__"
            self._choice_key_to_path[key] = str(path)
            table.add_row(str(path), key=key)
        yield table
        with Horizontal(classes="buttons"):
            yield Button("Process", id="process", variant="primary")
            yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return
        if event.button.id == "process":
            table = self.query_one("#choices", DataTable)
            key = None
            if table.cursor_row is not None:
                if hasattr(table, "get_row_key"):
                    key = table.get_row_key(table.cursor_row)  # type: ignore[attr-defined]
                else:
                    try:
                        key = list(getattr(table, "rows", {}).keys())[int(table.cursor_row)]
                    except Exception:
                        key = None
            value = getattr(key, "value", None) if key is not None else None
            selected_key = str(value) if value is not None else "__full__"
            if selected_key == "__full__":
                input_path = None
            else:
                input_path = self._choice_key_to_path.get(selected_key)
            self.dismiss({"input_path": input_path})


class CliperTUI(App):
    TITLE = "CLIPER"
    SUB_TITLE = "Video Clipper (Textual)"

    CSS = """
    Screen { layout: vertical; }
    #main { height: 1fr; }
    #library { width: 2fr; }
    #right { width: 1fr; }
    #details { height: auto; padding: 1 2; border: solid gray; }
    #jobs { height: 12; border: solid gray; }
    #logs { height: 1fr; border: solid gray; }
    .label { margin: 1 2 0 2; }
    #title { padding: 1 2; text-style: bold; }
    Input { margin: 0 2; }
    Checkbox { margin: 1 2; }
    .buttons { margin: 1 2; }
    """

    BINDINGS = [
        Binding("a", "add_videos", "Add Videos"),
        Binding("space", "toggle_select", "Select"),
        Binding("t", "enqueue_transcribe", "Transcribe"),
        Binding("c", "enqueue_clips", "Clips"),
        Binding("e", "enqueue_export", "Export"),
        Binding("p", "enqueue_process_shorts", "Process Shorts"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.state_manager = get_state_manager()
        self.videos: List[Dict[str, str]] = []
        self.selected_video_id: Optional[str] = None
        self.selected_video_ids: Set[str] = set()

        self._running_job_id: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            yield DataTable(id="library")
            with Vertical(id="right"):
                yield Static("Select a video", id="details")
                yield DataTable(id="jobs")
                yield RichLog(id="logs", markup=True)
        yield Footer()

    def on_mount(self) -> None:
        library = self.query_one("#library", DataTable)
        library.cursor_type = "row"
        library.add_columns("✓", "Video", "Status")

        jobs = self.query_one("#jobs", DataTable)
        jobs.cursor_type = "row"
        jobs.add_columns("Job", "State", "Progress", "Videos", "Steps")

        logs = self.query_one("#logs", RichLog)
        logs.write("[dim]Ready.[/dim]")

        self.refresh_all()

    def refresh_all(self) -> None:
        self.refresh_library()
        self.refresh_jobs()
        self._maybe_start_next_job()

    def refresh_library(self) -> None:
        self.videos = [
            {"video_id": v["video_id"], "filename": v["filename"], "path": v["path"]}
            for v in load_registered_videos(self.state_manager)
        ]
        table = self.query_one("#library", DataTable)
        table.clear()

        for video in self.videos:
            state = self.state_manager.get_video_state(video["video_id"]) or {}
            parts = []
            if state.get("transcribed"):
                parts.append("Transcribed")
            if state.get("clips_generated"):
                parts.append(f"Clips: {len(state.get('clips', []) or [])}")
            if state.get("clips_exported"):
                parts.append("Exported")
            if state.get("shorts_exported"):
                parts.append("Short exported")
            status = " | ".join(parts) if parts else "Ready"
            marker = "✓" if video["video_id"] in self.selected_video_ids else ""
            table.add_row(marker, video["filename"], status, key=video["video_id"])

        if self.videos:
            table.focus()

    def refresh_jobs(self) -> None:
        table = self.query_one("#jobs", DataTable)
        table.clear()
        jobs = self.state_manager.list_jobs()

        def format_progress(st: Dict) -> str:
            cur = int(st.get("progress_current") or 0)
            total = int(st.get("progress_total") or 0)
            if total <= 0:
                return "-"
            return f"{cur}/{total}"

        for job_id, job in jobs.items():
            spec = job.get("spec") or {}
            st = job.get("status") or {}
            state = str(st.get("state") or "pending")
            progress = format_progress(st)
            videos = ",".join(spec.get("video_ids") or [])
            steps = ",".join(spec.get("steps") or [])
            table.add_row(job_id, state, progress, videos, steps, key=job_id)

    def action_refresh(self) -> None:
        self.refresh_all()

    def action_toggle_select(self) -> None:
        table = self.query_one("#library", DataTable)
        if table.cursor_row is None:
            return
        row_key = None
        if hasattr(table, "get_row_key"):
            row_key = table.get_row_key(table.cursor_row)  # type: ignore[attr-defined]
        else:
            try:
                row_key = list(getattr(table, "rows", {}).keys())[int(table.cursor_row)]
            except Exception:
                row_key = None
        if row_key is None:
            return
        video_id = getattr(row_key, "value", None) or str(row_key)
        if video_id in self.selected_video_ids:
            self.selected_video_ids.remove(video_id)
        else:
            self.selected_video_ids.add(video_id)
        self.refresh_library()

    async def action_add_videos(self) -> None:
        # Use a non-blocking modal flow to avoid Textual worker requirements that can
        # raise `NoActiveWorker` under `push_screen_wait(...)` in some environments.
        await self.push_screen(AddVideosModal(), callback=self._on_add_videos_dismissed)

    def _on_add_videos_dismissed(self, result: Optional[Dict[str, object]]) -> None:
        if not result:
            return

        url = str(result.get("url") or "").strip()
        paths_raw = str(result.get("paths") or "").strip()
        recursive = bool(result.get("recursive"))

        logs = self.query_one("#logs", RichLog)

        if url:
            logs.write(f"[cyan]Downloading:[/cyan] {url}")

            def download_and_register() -> None:
                from src.downloader import YoutubeDownloader
                from src.core.dependency_manager import DependencyProgress, DependencyReporter, DependencyStatus

                call_from_thread = self.call_from_thread

                class _TUIDownloadReporter(DependencyReporter):
                    def __init__(self, call_from_thread):
                        self._call_from_thread = call_from_thread
                        self._last_line: str = ""

                    def report(self, event: DependencyProgress) -> None:
                        if event.status == DependencyStatus.DOWNLOADING:
                            if not event.message:
                                return
                            if event.message == self._last_line:
                                return
                            self._last_line = event.message
                            self._call_from_thread(logs.write, f"[dim]{event.message}[/dim]")
                        elif event.status == DependencyStatus.ERROR:
                            self._call_from_thread(logs.write, f"[red]{event.description} failed:[/red] {event.message}")
                        elif event.status == DependencyStatus.DONE:
                            if event.message:
                                self._call_from_thread(logs.write, f"[green]Saved:[/green] {event.message}")

                    def is_cancelled(self) -> bool:
                        return False

                downloader = YoutubeDownloader(download_dir="downloads", reporter=_TUIDownloadReporter(call_from_thread))
                downloaded = downloader.download(url)
                if not downloaded:
                    self.call_from_thread(logs.write, f"[red]Download failed:[/red] {url}")
                    return

                video_path = Path(downloaded)
                register_local_videos(self.state_manager, [video_path])
                self.call_from_thread(logs.write, f"[green]Downloaded:[/green] {video_path.name}")
                self.call_from_thread(self.refresh_all)

            self.run_worker(download_and_register, thread=True)

        if paths_raw:
            def collect_and_register_local() -> None:
                try:
                    paths, errors = collect_local_video_paths(paths_raw, recursive=recursive)
                    registered_count = 0
                    if paths:
                        registered = register_local_videos(self.state_manager, paths)
                        registered_count = len(registered)
                    self.call_from_thread(self._on_local_videos_registered, errors, registered_count)
                except Exception as e:
                    self.call_from_thread(logs.write, f"[red]Failed to register local videos:[/red] {e}")

            self.run_worker(collect_and_register_local, thread=True)

    def _on_local_videos_registered(self, errors: List[str], registered_count: int) -> None:
        logs = self.query_one("#logs", RichLog)
        for err in errors:
            logs.write(f"[yellow]{err}[/yellow]")
        if registered_count <= 0:
            logs.write("[yellow]No supported videos found to register.[/yellow]")
            return
        logs.write(f"[green]Registered {registered_count} video(s).[/green]")
        self.refresh_all()

    def _selected_or_current_video_ids(self) -> List[str]:
        if self.selected_video_ids:
            return sorted(self.selected_video_ids)
        if self.selected_video_id:
            return [self.selected_video_id]
        return []

    def _enqueue_job(self, steps: List[JobStep], *, settings: Optional[Dict[str, object]] = None) -> None:
        video_ids = self._selected_or_current_video_ids()
        if not video_ids:
            self.query_one("#logs", RichLog).write("[yellow]No videos selected.[/yellow]")
            return

        job_id = self.state_manager.create_job_id()
        spec = JobSpec(job_id=job_id, video_ids=video_ids, steps=steps, settings=dict(settings or {}))
        self.state_manager.enqueue_job(spec.to_dict(), initial_status={"state": "pending", "progress_current": 0, "progress_total": len(video_ids) * len(steps)})
        self.refresh_jobs()
        self._maybe_start_next_job()

    def action_enqueue_transcribe(self) -> None:
        self._enqueue_job([JobStep.TRANSCRIBE])

    def action_enqueue_clips(self) -> None:
        self._enqueue_job([JobStep.GENERATE_CLIPS])

    def action_enqueue_export(self) -> None:
        self._enqueue_job([JobStep.EXPORT_CLIPS])

    async def action_enqueue_process_shorts(self) -> None:
        video_ids = self._selected_or_current_video_ids()
        if not video_ids:
            self.query_one("#logs", RichLog).write("[yellow]No videos selected.[/yellow]")
            return

        # Keep this flow explicit: transcription + shorts export, no analysis / clip generation.
        if len(video_ids) != 1:
            self._enqueue_job([JobStep.TRANSCRIBE, JobStep.EXPORT_SHORTS])
            return

        video_id = video_ids[0]
        state = self.state_manager.get_video_state(video_id) or {}
        exported_clips = state.get("exported_clips") or []
        if not exported_clips:
            self._enqueue_job([JobStep.TRANSCRIBE, JobStep.EXPORT_SHORTS])
            return

        await self.push_screen(
            ProcessShortsModal(title="Process Shorts", choices=[str(p) for p in exported_clips]),
            callback=lambda result: self._on_process_shorts_dismissed(video_id, result),
        )

    def _on_process_shorts_dismissed(self, video_id: str, result: Optional[Dict[str, object]]) -> None:
        if result is None:
            return

        input_path = result.get("input_path")
        settings: Dict[str, object] = {}
        if input_path:
            settings = {"shorts": {"input_paths": {video_id: str(input_path)}}}

        self._enqueue_job([JobStep.TRANSCRIBE, JobStep.EXPORT_SHORTS], settings=settings)

    def _maybe_start_next_job(self) -> None:
        if self._running_job_id is not None:
            return

        next_job_id = self.state_manager.dequeue_next_job_id()
        if not next_job_id:
            return

        job = self.state_manager.get_job(next_job_id) or {}
        spec_dict = job.get("spec") or {}
        try:
            spec = JobSpec.from_dict(spec_dict)
        except Exception as e:
            self.query_one("#logs", RichLog).write(f"[red]Invalid job spec {next_job_id}: {e}[/red]")
            self.state_manager.update_job_status(next_job_id, {"state": "failed", "error": str(e)})
            self.refresh_jobs()
            return

        self._running_job_id = spec.job_id
        self.state_manager.update_job_status(spec.job_id, {"state": "running"})
        self.refresh_jobs()

        def emit(event: object) -> None:
            self.call_from_thread(self._handle_core_event, event)

        def run() -> None:
            runner = JobRunner(self.state_manager, emit=emit)
            status = runner.run_job(spec)
            self.call_from_thread(self.state_manager.update_job_status, spec.job_id, status.to_dict())
            self.call_from_thread(self._on_job_finished, spec.job_id)

        self.run_worker(run, thread=True)

    def _on_job_finished(self, job_id: str) -> None:
        self._running_job_id = None
        self.refresh_all()

    def _handle_core_event(self, event: object) -> None:
        logs = self.query_one("#logs", RichLog)

        if isinstance(event, LogEvent):
            prefix = f"[{event.level.value}]".upper()
            logs.write(f"[dim]{event.ts}[/dim] {prefix} {event.message}")
            return

        if isinstance(event, ProgressEvent):
            self.state_manager.update_job_status(
                event.job_id,
                {"progress_current": event.current, "progress_total": event.total, "label": event.label},
            )
            self.refresh_jobs()
            return

        if isinstance(event, JobStatusEvent):
            update: Dict[str, object] = {"state": event.state.value}
            if event.error:
                update["error"] = event.error
            self.state_manager.update_job_status(event.job_id, update)
            self.refresh_jobs()
            return

        if isinstance(event, StateEvent):
            # Estado del video ya fue persistido por StateManager en el runner; refrescamos UI.
            self.refresh_library()
            return

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id != "library":
            return

        self.selected_video_id = getattr(event.row_key, "value", None) or str(event.row_key)
        state = self.state_manager.get_video_state(self.selected_video_id) or {}
        try:
            details = self.query_one("#details", Static)
        except Exception:
            return

        filename = state.get("filename") or self.selected_video_id
        video_path = state.get("video_path") or ""
        content_type = state.get("content_type") or "tutorial"
        lines = [
            f"Video: {filename}",
            f"Type: {content_type}",
            "",
            f"Path: {video_path}",
            "",
            f"Transcribed: {bool(state.get('transcribed'))}",
            f"Clips generated: {bool(state.get('clips_generated'))}",
            f"Clips exported: {bool(state.get('clips_exported'))}",
            f"Short exported: {bool(state.get('shorts_exported'))}",
        ]
        details.update("\n".join(lines))


if __name__ == "__main__":
    CliperTUI().run()
