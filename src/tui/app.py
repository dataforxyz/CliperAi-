# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.events import Resize
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, DataTable, Footer, Header, Input, RichLog, Static

# Minimum terminal size for proper rendering
MIN_WIDTH = 80
MIN_HEIGHT = 20

from src.utils import get_state_manager
from src.utils.open_path import open_path
from src.utils.video_registry import load_registered_videos
from src.utils.video_registry import collect_local_video_paths, register_local_videos

from src.core.events import JobStatusEvent, LogEvent, ProgressEvent, StateEvent
from src.core.job_runner import JobRunner
from src.core.models import JobSpec, JobState, JobStep
from src.config.settings_schema import iter_app_setting_groups, list_app_settings_by_group
from src.core.dependency_manager import (
    DependencyProgress,
    DependencyReporter,
    DependencySpec,
    DependencyStatus,
    build_required_dependencies,
    ensure_all_required,
)
from src.tui.setup_wizard import SetupWizardModal


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


class CustomShortsModal(ModalScreen[Optional[Dict[str, object]]]):
    """Modal for custom shorts processing with options for subtitles, logo, face tracking, and trim."""

    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
    ]

    def __init__(self, *, state_manager, choices: Optional[List[str]] = None):
        super().__init__()
        self._state_manager = state_manager
        self._choices = choices or []
        self._choice_key_to_path: Dict[str, str] = {}

    def on_mount(self) -> None:
        # Load current settings as defaults
        settings = self._state_manager.load_settings()

        # Populate fields with current settings
        self.query_one("#subtitle_preset", Input).value = settings.get("subtitle_preset", "default")
        self.query_one("#add_logo", Checkbox).value = True
        self.query_one("#logo_position", Input).value = settings.get("logo_position", "top-right")
        self.query_one("#enable_face_tracking", Checkbox).value = settings.get("enable_face_tracking", False)
        self.query_one("#face_tracking_strategy", Input).value = settings.get("face_tracking_strategy", "keep_in_frame")

        # Trim settings - enable if either value is non-zero
        trim_start = int(settings.get("trim_ms_start", 0))
        trim_end = int(settings.get("trim_ms_end", 0))
        self.query_one("#enable_trim", Checkbox).value = (trim_start > 0 or trim_end > 0)
        self.query_one("#trim_ms_start", Input).value = str(trim_start)
        self.query_one("#trim_ms_end", Input).value = str(trim_end)

        # Focus the first input or source table if choices exist
        if self._choices:
            self.query_one("#source_table", DataTable).focus()
        else:
            self.query_one("#subtitle_preset", Input).focus()

    def compose(self) -> ComposeResult:
        yield Static("Custom Shorts Processing", id="title")
        yield Static("Configure options for shorts export (Shift+P)", id="custom_shorts_subtitle")

        with Vertical(id="custom_shorts_modal"):
            with ScrollableContainer(id="custom_shorts_body"):
                # Source selection (if there are exported clips)
                if self._choices:
                    with Vertical(classes="settings-group"):
                        yield Static("Source Selection", classes="group-title")
                        table = DataTable(id="source_table")
                        table.add_columns("Source")
                        table.add_row("Full video", key="__full__")
                        self._choice_key_to_path.clear()
                        for idx, path in enumerate(self._choices):
                            key = f"__choice_{idx}__"
                            self._choice_key_to_path[key] = str(path)
                            table.add_row(str(path), key=key)
                        yield table

                # Subtitle settings
                with Vertical(classes="settings-group"):
                    yield Static("Subtitles", classes="group-title")
                    with Vertical(classes="setting-field"):
                        yield Static("Preset style:", classes="field-label")
                        yield Static("Options: default, bold, yellow, tiktok, small, tiny", classes="help-text")
                        yield Input(placeholder="default", id="subtitle_preset")

                # Logo settings
                with Vertical(classes="settings-group"):
                    yield Static("Logo / Watermark", classes="group-title")
                    yield Checkbox("Add logo to video", id="add_logo", value=True)
                    with Vertical(classes="setting-field"):
                        yield Static("Logo position:", classes="field-label")
                        yield Static("Options: top-right, top-left, bottom-right, bottom-left", classes="help-text")
                        yield Input(placeholder="top-right", id="logo_position")

                # Face tracking settings
                with Vertical(classes="settings-group"):
                    yield Static("Face Tracking (9:16 only)", classes="group-title")
                    yield Checkbox("Enable face tracking", id="enable_face_tracking", value=False)
                    with Vertical(classes="setting-field"):
                        yield Static("Strategy:", classes="field-label")
                        yield Static("keep_in_frame (less jittery) or centered (always center face)", classes="help-text")
                        yield Input(placeholder="keep_in_frame", id="face_tracking_strategy")

                # Trim settings
                with Vertical(classes="settings-group"):
                    yield Static("Dead Space Trimming", classes="group-title")
                    yield Static("Trim silence/dead space from clip boundaries", classes="group-desc")
                    yield Checkbox("Enable trimming", id="enable_trim", value=False)
                    with Vertical(classes="setting-field"):
                        yield Static("Trim from start (milliseconds):", classes="field-label")
                        yield Input(placeholder="0", id="trim_ms_start")
                    with Vertical(classes="setting-field"):
                        yield Static("Trim from end (milliseconds):", classes="field-label")
                        yield Input(placeholder="0", id="trim_ms_end")

            with Horizontal(classes="buttons"):
                yield Button("Process", id="process", variant="primary")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return

        if event.button.id == "process":
            # Gather all settings
            result: Dict[str, object] = {}

            # Get source selection
            if self._choices:
                table = self.query_one("#source_table", DataTable)
                key = None
                if table.cursor_row is not None:
                    if hasattr(table, "get_row_key"):
                        key = table.get_row_key(table.cursor_row)
                    else:
                        try:
                            key = list(getattr(table, "rows", {}).keys())[int(table.cursor_row)]
                        except Exception:
                            key = None
                value = getattr(key, "value", None) if key is not None else None
                selected_key = str(value) if value is not None else "__full__"
                if selected_key != "__full__":
                    result["input_path"] = self._choice_key_to_path.get(selected_key)

            # Subtitle settings
            subtitle_preset = self.query_one("#subtitle_preset", Input).value.strip().lower()
            if subtitle_preset and subtitle_preset in {"default", "bold", "yellow", "tiktok", "small", "tiny"}:
                result["subtitle_style"] = subtitle_preset

            # Logo settings
            result["add_logo"] = self.query_one("#add_logo", Checkbox).value
            logo_position = self.query_one("#logo_position", Input).value.strip().lower()
            if logo_position in {"top-right", "top-left", "bottom-right", "bottom-left"}:
                result["logo_position"] = logo_position

            # Face tracking settings
            result["enable_face_tracking"] = self.query_one("#enable_face_tracking", Checkbox).value
            face_strategy = self.query_one("#face_tracking_strategy", Input).value.strip().lower()
            if face_strategy in {"keep_in_frame", "centered"}:
                result["face_tracking_strategy"] = face_strategy

            # Trim settings - only apply if toggle is enabled
            enable_trim = self.query_one("#enable_trim", Checkbox).value
            if enable_trim:
                try:
                    trim_start = int(self.query_one("#trim_ms_start", Input).value.strip() or "0")
                    result["trim_ms_start"] = max(0, trim_start)
                except ValueError:
                    result["trim_ms_start"] = 0

                try:
                    trim_end = int(self.query_one("#trim_ms_end", Input).value.strip() or "0")
                    result["trim_ms_end"] = max(0, trim_end)
                except ValueError:
                    result["trim_ms_end"] = 0
            else:
                result["trim_ms_start"] = 0
                result["trim_ms_end"] = 0

            self.dismiss(result)


class SettingsModal(ModalScreen[Optional[Dict[str, object]]]):
    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
    ]

    def __init__(self, *, state_manager):
        super().__init__()
        self._state_manager = state_manager
        self._errors: Dict[str, str] = {}
        self._validated: Dict[str, object] = {}

    def on_mount(self) -> None:
        settings_by_group = list_app_settings_by_group()
        all_settings = [s for group in iter_app_setting_groups() for s in settings_by_group.get(group.key, [])]
        for setting in all_settings:
            current = self._state_manager.get_setting(setting.key, setting.default)
            input_widget = self.query_one(f"#setting_{setting.key}", Input)
            # Preserve valid falsy values (e.g., False, 0) and only fall back when unset/blank.
            if current is None:
                input_widget.value = str(setting.default)
                continue
            text = str(current)
            if setting.python_type is str and text.strip() == "":
                input_widget.value = str(setting.default)
            else:
                input_widget.value = text

        if all_settings:
            self.query_one(f"#setting_{all_settings[0].key}", Input).focus()

    def compose(self) -> ComposeResult:
        yield Static("Settings", id="title")
        yield Static("Changes auto-save. Press Esc to close.", id="settings_subtitle")

        with Vertical(id="settings_modal"):
            with ScrollableContainer(id="settings_body"):
                settings_by_group = list_app_settings_by_group()
                for group in iter_app_setting_groups():
                    group_settings = settings_by_group.get(group.key, [])
                    if not group_settings:
                        continue

                    with Vertical(classes="settings-group", id=f"settings_group_{group.key}"):
                        yield Static(group.title, classes="group-title")
                        if group.description:
                            yield Static(group.description, classes="group-desc")

                        for setting in group_settings:
                            with Vertical(classes="setting-field", id=f"setting_field_{setting.key}"):
                                yield Static(setting.label, classes="field-label")
                                if setting.help_text:
                                    yield Static(setting.help_text, classes="help-text")
                                yield Static(f"Default: {setting.default}", classes="default-hint")
                                yield Input(placeholder=setting.placeholder, id=f"setting_{setting.key}")
                                yield Static("", id=f"setting_{setting.key}_error", classes="error-text")

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id and event.input.id.startswith("setting_"):
            self._validate_and_save()

    def _validate_and_save(self) -> None:
        self._errors.clear()
        self._validated = {}

        settings_by_group = list_app_settings_by_group()
        all_settings = [s for group in iter_app_setting_groups() for s in settings_by_group.get(group.key, [])]
        for setting in all_settings:
            raw_value = self.query_one(f"#setting_{setting.key}", Input).value
            try:
                self._validated[setting.key] = setting.validate_from_text(raw_value)
            except Exception as e:
                msg = str(e).strip() or "Invalid value"
                self._errors[setting.key] = msg

        self._render_validation_state()

        # Auto-save valid settings
        if not self._errors:
            for setting in all_settings:
                new_value = self._validated.get(setting.key)
                current = self._state_manager.get_setting(setting.key, setting.default)
                if current != new_value:
                    self._state_manager.set_setting(setting.key, new_value)

    def _render_validation_state(self) -> None:
        settings_by_group = list_app_settings_by_group()
        all_settings = [s for group in iter_app_setting_groups() for s in settings_by_group.get(group.key, [])]
        for setting in all_settings:
            error_text = self._errors.get(setting.key, "")
            error_widget = self.query_one(f"#setting_{setting.key}_error", Static)
            error_widget.update(error_text)
            error_widget.display = bool(error_text)

            input_widget = self.query_one(f"#setting_{setting.key}", Input)
            if error_text:
                input_widget.add_class("invalid")
            else:
                input_widget.remove_class("invalid")


class DependencyModal(ModalScreen[Optional[Dict[str, object]]]):
    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
    ]

    def __init__(self, *, specs: List[DependencySpec], auto_install: bool = False):
        super().__init__()
        self._specs = specs
        self._auto_install = auto_install
        self._status: Dict[str, str] = {}  # key -> status text
        self._is_downloading = False
        self._cancelled = False

    def compose(self) -> ComposeResult:
        yield Static("Dependencies", id="title")
        yield Static(
            "Required models for transcription. Missing items will be downloaded.",
            id="dep_subtitle",
        )

        with Vertical(id="dep_modal"):
            with ScrollableContainer(id="dep_body"):
                table = DataTable(id="dep_table")
                table.add_columns("Dependency", "Status")
                yield table
                yield Static("", id="dep_progress_text")

            with Horizontal(classes="buttons", id="dep_buttons"):
                yield Button("Install Missing", id="install", variant="primary")
                yield Button("Close", id="close")

    def on_mount(self) -> None:
        self._refresh_table()
        if self._auto_install:
            self.call_later(self._start_install)

    def _refresh_table(self) -> None:
        table = self.query_one("#dep_table", DataTable)
        table.clear()
        for spec in self._specs:
            status = self._status.get(spec.key, "Checking...")
            table.add_row(spec.description, status, key=spec.key)

    def _update_status(self, key: str, status: str) -> None:
        self._status[key] = status
        try:
            table = self.query_one("#dep_table", DataTable)
            for row_key in list(table.rows.keys()):
                if getattr(row_key, "value", str(row_key)) == key:
                    row_idx = table.get_row_index(row_key)
                    spec_desc = next((s.description for s in self._specs if s.key == key), key)
                    table.update_cell_at((row_idx, 1), status)
                    break
        except Exception:
            pass

    def _update_progress_text(self, text: str) -> None:
        try:
            self.query_one("#dep_progress_text", Static).update(text)
        except Exception:
            pass

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            if self._is_downloading:
                self._cancelled = True
            self.dismiss({"cancelled": self._cancelled})
            return

        if event.button.id == "install":
            self._start_install()

    def _start_install(self) -> None:
        if self._is_downloading:
            return
        self._is_downloading = True
        self._cancelled = False

        try:
            self.query_one("#install", Button).disabled = True
        except Exception:
            pass

        # Check current status first
        for spec in self._specs:
            self._update_status(spec.key, "Checking...")

        def run_ensure() -> None:
            call_from_thread = self.call_from_thread

            class _TUIDependencyReporter(DependencyReporter):
                def __init__(reporter_self):
                    reporter_self._modal = self

                def report(reporter_self, event: DependencyProgress) -> None:
                    status_text = ""
                    if event.status == DependencyStatus.CHECKING:
                        status_text = "Checking..."
                    elif event.status == DependencyStatus.DOWNLOADING:
                        status_text = f"Downloading... (attempt {event.attempt})"
                    elif event.status == DependencyStatus.SKIPPED:
                        status_text = "[green]Installed[/green]"
                    elif event.status == DependencyStatus.DONE:
                        status_text = "[green]Downloaded[/green]"
                    elif event.status == DependencyStatus.ERROR:
                        status_text = f"[red]Error: {event.message}[/red]"

                    call_from_thread(reporter_self._modal._update_status, event.key, status_text)
                    progress_text = f"[{event.index}/{event.total}] {event.description}"
                    if event.message and event.status == DependencyStatus.DOWNLOADING:
                        progress_text += f" - {event.message}"
                    call_from_thread(reporter_self._modal._update_progress_text, progress_text)

                def is_cancelled(reporter_self) -> bool:
                    return reporter_self._modal._cancelled

            reporter = _TUIDependencyReporter()
            result = ensure_all_required(self._specs, reporter=reporter, max_attempts=2)

            def finish():
                self._is_downloading = False
                try:
                    self.query_one("#install", Button).disabled = False
                except Exception:
                    pass

                if result.canceled:
                    self._update_progress_text("[yellow]Cancelled[/yellow]")
                elif result.failed:
                    failed_list = ", ".join(result.failed.keys())
                    self._update_progress_text(f"[red]Some failed: {failed_list}[/red]")
                else:
                    self._update_progress_text("[green]All dependencies ready![/green]")

            call_from_thread(finish)

        self.app.run_worker(run_ensure, thread=True)


def check_missing_dependencies(specs: List[DependencySpec]) -> List[DependencySpec]:
    """Return list of specs that are not yet installed."""
    missing = []
    for spec in specs:
        try:
            if not spec.check():
                missing.append(spec)
        except Exception:
            missing.append(spec)
    return missing


class CliperTUI(App):
    TITLE = "CLIPER"
    SUB_TITLE = "Video Clipper (Textual)"

    CSS = """
    Screen { layout: vertical; }
    #main { height: 1fr; }

    /* Library panel - responsive width with constraints */
    #library {
        width: 2fr;
        min-width: 30;
        max-width: 100;
    }

    /* Right panel - collapsible on narrow terminals */
    #right {
        width: 1fr;
        min-width: 25;
    }

    /* Details section - scrollable for long content */
    #details {
        height: auto;
        max-height: 12;
        padding: 1 2;
        border: solid gray;
        overflow-y: auto;
    }

    #open-actions { height: auto; padding: 1 2; }

    /* Jobs table - scrollable with min/max height */
    #jobs {
        height: 12;
        min-height: 5;
        max-height: 20;
        border: solid gray;
        overflow-y: auto;
    }

    /* Logs - flexible height, scrollable */
    #logs {
        height: 1fr;
        min-height: 8;
        border: solid gray;
    }

    /* Size warning overlay */
    #size-warning {
        dock: bottom;
        height: auto;
        background: $warning;
        color: $text;
        padding: 0 1;
        display: none;
    }

    .label { margin: 1 2 0 2; }
    #title { padding: 1 2; text-style: bold; }
    Input { margin: 0 2; }
    Checkbox { margin: 1 2; }
    .buttons { margin: 1 2; }

    /* Settings modal - scoped styles so other screens don't regress */
    #settings_modal {
        width: 96%;
        max-width: 120;
        height: 1fr;
        min-height: 14;
        margin: 1 2;
        border: heavy $panel;
        background: $surface;
    }

    #settings_subtitle {
        margin: 0 2 1 2;
        color: $text 70%;
    }

    #settings_body { padding: 1 2; height: 1fr; }

    .settings-group { margin-top: 1; padding: 1 1; border: solid $panel; height: auto; }
    .group-title { text-style: bold; margin: 0 0 1 0; }
    .group-desc { color: $text 70%; margin: 0 0 1 0; }

    .setting-field { margin: 1 0; height: auto; }
    .field-label { text-style: bold; }
    .help-text { color: $text 70%; }
    .default-hint { color: $text 60%; }
    .error-text { color: $error; margin-top: 1; height: auto; }

    #settings_modal Input { margin: 0; }
    Input.invalid { border: heavy $error; }

    /* Dependency modal styles */
    #dep_modal {
        width: 90%;
        max-width: 100;
        height: auto;
        min-height: 12;
        margin: 1 2;
        border: heavy $panel;
        background: $surface;
    }

    #dep_subtitle {
        margin: 0 2 1 2;
        color: $text 70%;
    }

    #dep_body { padding: 1 2; height: auto; }

    #dep_table {
        height: 10;
        min-height: 5;
        border: solid $panel;
    }

    #dep_progress_text {
        margin-top: 1;
        color: $text 80%;
    }

    #dep_buttons {
        margin: 0;
        padding: 1 2;
        border-top: solid $panel;
        background: $surface;
    }

    /* Custom shorts modal styles */
    #custom_shorts_modal {
        width: 96%;
        max-width: 100;
        height: 1fr;
        min-height: 14;
        margin: 1 2;
        border: heavy $panel;
        background: $surface;
    }

    #custom_shorts_subtitle {
        margin: 0 2 1 2;
        color: $text 70%;
    }

    #custom_shorts_body { padding: 1 2; height: 1fr; }

    #source_table {
        height: 6;
        min-height: 4;
        border: solid $panel;
        margin-bottom: 1;
    }

    /* Compact mode - triggered by on_resize handler */
    .compact #right { display: none; }
    .compact #library { width: 100%; max-width: 100%; }
    """

    BINDINGS = [
        Binding("a", "add_videos", "Add Videos"),
        Binding("space", "toggle_select", "Select"),
        Binding("t", "enqueue_transcribe", "Transcribe"),
        Binding("c", "enqueue_clips", "Clips"),
        Binding("e", "enqueue_export", "Export"),
        Binding("p", "enqueue_process_shorts", "Process Shorts"),
        Binding("P", "custom_shorts", "Custom Shorts"),
        Binding("r", "refresh", "Refresh"),
        Binding("s", "settings", "Settings"),
        Binding("w", "setup_wizard", "Setup Wizard"),
        Binding("d", "dependencies", "Dependencies"),
        Binding("backslash", "toggle_sidebar", "Toggle Sidebar"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self):
        super().__init__()
        self.state_manager = get_state_manager()
        self.videos: List[Dict[str, str]] = []
        self.selected_video_id: Optional[str] = None
        self.selected_video_ids: Set[str] = set()
        self.selected_job_id: Optional[str] = None

        self._running_job_id: Optional[str] = None
        self._selected_run_output_dir: Optional[Path] = None
        self._selected_final_video_path: Optional[Path] = None
        self._startup_dep_check_done = False
        self._startup_wizard_check_done = False

    def _load_selected_job_open_targets(self, job_id: Optional[str]) -> None:
        run_output_dir: Optional[Path] = None
        final_video_path: Optional[Path] = None
        succeeded = False

        if job_id:
            job = self.state_manager.get_job(job_id) or {}
            status = (job.get("status") or {}) if isinstance(job, dict) else {}
            succeeded = status.get("state") == "succeeded"
            run_output_dir_raw = status.get("run_output_dir")
            final_video_path_raw = status.get("final_video_path")
            run_output_dir = Path(run_output_dir_raw) if run_output_dir_raw else None
            final_video_path = Path(final_video_path_raw) if final_video_path_raw else None

            if succeeded and run_output_dir and run_output_dir.exists() and (not final_video_path or not final_video_path.exists()):
                try:
                    mp4s = list(run_output_dir.rglob("*.mp4"))
                    if mp4s:
                        final_video_path = max(mp4s, key=lambda p: p.stat().st_mtime)
                except Exception:
                    final_video_path = None

        self._selected_run_output_dir = run_output_dir
        self._selected_final_video_path = final_video_path

        try:
            open_video_btn = self.query_one("#open_video", Button)
            open_output_btn = self.query_one("#open_output", Button)
            open_video_btn.disabled = not (succeeded and self._selected_final_video_path and self._selected_final_video_path.exists())
            # Output folder button is always enabled - falls back to general output/ folder
            open_output_btn.disabled = False
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"Terminal too small! Resize to at least {MIN_WIDTH}x{MIN_HEIGHT}", id="size-warning")
        with Horizontal(id="main"):
            yield DataTable(id="library")
            with Vertical(id="right"):
                yield Static("Select a video", id="details")
                with Horizontal(id="open-actions"):
                    yield Button("Settings", id="settings")
                    yield Button("Open Video", id="open_video", disabled=True)
                    yield Button("Open Output Folder", id="open_output")
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

        # Check initial size and apply responsive layout
        self._update_layout_for_size(self.size.width, self.size.height)

        self.refresh_all()

        # Check for first run and show setup wizard
        if not self._startup_wizard_check_done:
            self._startup_wizard_check_done = True
            if self.state_manager.is_first_run():
                self.call_later(self._show_setup_wizard)
                return  # Skip dependency check until wizard is done

        # Check dependencies on startup
        if not self._startup_dep_check_done:
            self._startup_dep_check_done = True
            self.call_later(self._check_startup_dependencies)

    def on_resize(self, event: Resize) -> None:
        """Handle terminal resize - toggle compact mode and show warnings."""
        self._update_layout_for_size(event.size.width, event.size.height)

    def _update_layout_for_size(self, width: int, height: int) -> None:
        """Update layout based on terminal dimensions."""
        # Show/hide size warning
        try:
            warning = self.query_one("#size-warning", Static)
            too_small = width < MIN_WIDTH or height < MIN_HEIGHT
            warning.styles.display = "block" if too_small else "none"
        except Exception:
            pass

        # Toggle compact mode for narrow terminals (hide right panel)
        compact_threshold = 100
        if width < compact_threshold:
            self.add_class("compact")
        else:
            self.remove_class("compact")

    def action_toggle_sidebar(self) -> None:
        """Manually toggle the right sidebar (details/jobs/logs panel)."""
        self.toggle_class("compact")

    def refresh_all(self) -> None:
        self.refresh_library()
        self.refresh_jobs()
        if self.selected_job_id:
            self._load_selected_job_open_targets(self.selected_job_id)
        self._maybe_start_next_job()

    def _check_startup_dependencies(self) -> None:
        """Check for missing dependencies on startup and offer to install."""
        logs = self.query_one("#logs", RichLog)
        logs.write("[dim]Checking dependencies...[/dim]")

        def check_in_background() -> None:
            specs = build_required_dependencies()
            missing = check_missing_dependencies(specs)

            def show_result():
                if missing:
                    logs.write(f"[yellow]Missing {len(missing)} dependencies. Press 'd' to install.[/yellow]")
                    # Auto-show modal with missing dependencies
                    self.push_screen(
                        DependencyModal(specs=specs, auto_install=False),
                        callback=self._on_dependency_modal_dismissed,
                    )
                else:
                    logs.write("[green]All dependencies ready.[/green]")

            self.call_from_thread(show_result)

        self.run_worker(check_in_background, thread=True)

    async def action_dependencies(self) -> None:
        """Open the dependency management modal."""
        specs = build_required_dependencies()
        await self.push_screen(
            DependencyModal(specs=specs, auto_install=False),
            callback=self._on_dependency_modal_dismissed,
        )

    def _on_dependency_modal_dismissed(self, result: Optional[Dict[str, object]]) -> None:
        if not result:
            return
        logs = self.query_one("#logs", RichLog)
        if result.get("cancelled"):
            logs.write("[yellow]Dependency check cancelled.[/yellow]")
        else:
            logs.write("[green]Dependency check complete.[/green]")

    def _show_setup_wizard(self) -> None:
        """Show the setup wizard modal."""
        self.push_screen(
            SetupWizardModal(state_manager=self.state_manager),
            callback=self._on_setup_wizard_dismissed,
        )

    async def action_setup_wizard(self) -> None:
        """Open the setup wizard modal."""
        await self.push_screen(
            SetupWizardModal(state_manager=self.state_manager),
            callback=self._on_setup_wizard_dismissed,
        )

    def _on_setup_wizard_dismissed(self, result: Optional[Dict[str, object]]) -> None:
        logs = self.query_one("#logs", RichLog)
        if not result:
            logs.write("[yellow]Setup wizard cancelled.[/yellow]")
            # Still mark as completed so it doesn't show again
            self.state_manager.mark_wizard_completed()
        else:
            logs.write("[green]Setup complete! Settings saved.[/green]")

        # Now check dependencies after wizard is done
        if not self._startup_dep_check_done:
            self._startup_dep_check_done = True
            self.call_later(self._check_startup_dependencies)

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
        current_row = table.cursor_row
        self.refresh_library()
        # Move cursor to next row for easy bulk selection
        if current_row is not None and current_row + 1 < table.row_count:
            table.move_cursor(row=current_row + 1)

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

    async def action_settings(self) -> None:
        await self.push_screen(SettingsModal(state_manager=self.state_manager), callback=self._on_settings_dismissed)

    def _on_settings_dismissed(self, result: Optional[Dict[str, object]]) -> None:
        if not result:
            return
        logs = self.query_one("#logs", RichLog)
        changed = ", ".join(sorted(result.keys()))
        logs.write(f"[green]Settings saved:[/green] {changed}")
        self.refresh_all()

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

    async def action_custom_shorts(self) -> None:
        """Open the custom shorts modal (Shift+P) for configuring shorts export options."""
        video_ids = self._selected_or_current_video_ids()
        if not video_ids:
            self.query_one("#logs", RichLog).write("[yellow]No videos selected.[/yellow]")
            return

        # For single video with exported clips, show source selection
        choices: List[str] = []
        video_id = video_ids[0] if len(video_ids) == 1 else None
        if video_id:
            state = self.state_manager.get_video_state(video_id) or {}
            exported_clips = state.get("exported_clips") or []
            choices = [str(p) for p in exported_clips]

        await self.push_screen(
            CustomShortsModal(state_manager=self.state_manager, choices=choices),
            callback=lambda result: self._on_custom_shorts_dismissed(video_ids, result),
        )

    def _on_custom_shorts_dismissed(self, video_ids: List[str], result: Optional[Dict[str, object]]) -> None:
        if result is None:
            return

        # Build settings dict from modal result
        shorts_settings: Dict[str, object] = {}

        # Input path (if a specific clip was selected)
        if result.get("input_path") and len(video_ids) == 1:
            shorts_settings["input_paths"] = {video_ids[0]: str(result["input_path"])}

        # Subtitle style
        if result.get("subtitle_style"):
            shorts_settings["subtitle_style"] = result["subtitle_style"]

        # Logo settings
        shorts_settings["add_logo"] = result.get("add_logo", True)
        if result.get("logo_position"):
            shorts_settings["logo_position"] = result["logo_position"]

        # Face tracking settings - passed at top-level for job_runner
        export_settings: Dict[str, object] = {}
        export_settings["enable_face_tracking"] = result.get("enable_face_tracking", False)
        if result.get("face_tracking_strategy"):
            export_settings["face_tracking_strategy"] = result["face_tracking_strategy"]

        # Trim settings
        trim_start = int(result.get("trim_ms_start", 0))
        trim_end = int(result.get("trim_ms_end", 0))
        shorts_settings["trim_ms_start"] = trim_start
        shorts_settings["trim_ms_end"] = trim_end

        settings: Dict[str, object] = {"shorts": shorts_settings}
        if export_settings:
            settings["export"] = export_settings

        self._enqueue_job([JobStep.TRANSCRIBE, JobStep.EXPORT_SHORTS], settings=settings)
        self.query_one("#logs", RichLog).write(
            f"[cyan]Custom shorts job enqueued[/cyan] - Logo: {shorts_settings.get('add_logo')}, "
            f"Face tracking: {export_settings.get('enable_face_tracking')}, "
            f"Trim: {trim_start}ms/{trim_end}ms"
        )

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

        if self.selected_job_id is None:
            self.selected_job_id = job_id
        self._load_selected_job_open_targets(self.selected_job_id)

        logs = self.query_one("#logs", RichLog)
        job = self.state_manager.get_job(job_id) or {}
        status = (job.get("status") or {}) if isinstance(job, dict) else {}
        if status.get("state") == "succeeded":
            run_output_dir_raw = (status or {}).get("run_output_dir")
            final_video_path_raw = (status or {}).get("final_video_path")
            if final_video_path_raw:
                logs.write(f"[green]Job finished.[/green] Video: {final_video_path_raw}")
            if run_output_dir_raw:
                logs.write(f"[green]Output folder:[/green] {run_output_dir_raw}")
        else:
            err = status.get("error") or "Unknown error"
            logs.write(f"[red]Job failed:[/red] {err}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "settings":
            await self.action_settings()
            return

        if event.button.id == "open_video":
            if not self._selected_final_video_path:
                self.query_one("#logs", RichLog).write("[yellow]No final video available for the selected job.[/yellow]")
                return
            try:
                open_path(self._selected_final_video_path)
            except Exception as e:
                self.query_one("#logs", RichLog).write(f"[red]Failed to open video:[/red] {e}")
            return

        if event.button.id == "open_output":
            logs = self.query_one("#logs", RichLog)
            # Use job-specific output dir if available, otherwise fall back to general output folder
            target_dir = self._selected_run_output_dir
            if not target_dir or not target_dir.exists():
                target_dir = Path("output").resolve()
                if not target_dir.exists():
                    target_dir.mkdir(parents=True, exist_ok=True)
            logs.write(f"[dim]Opening folder:[/dim] {target_dir}")
            try:
                open_path(target_dir)
                logs.write("[green]Open command sent successfully[/green]")
            except Exception as e:
                logs.write(f"[red]Failed to open output folder:[/red] {e}")
            return

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
        if event.data_table.id == "jobs":
            self.selected_job_id = getattr(event.row_key, "value", None) or str(event.row_key)
            self._load_selected_job_open_targets(self.selected_job_id)
            return
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
