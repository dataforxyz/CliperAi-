# -*- coding: utf-8 -*-
"""
Setup Wizard - Guía inicial para configurar CLIPER
"""
from __future__ import annotations

from typing import Dict, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from src.config.settings_schema import SUBTITLE_PRESETS


# Platform presets con configuración optimizada para cada plataforma
PLATFORM_PRESETS: Dict[str, Dict[str, object]] = {
    "tiktok": {
        "label": "TikTok / Reels",
        "description": "Short vertical clips (15-60s, 9:16)",
        "min_clip_duration": 15,
        "max_clip_duration": 60,
        "default_aspect_ratio": "9:16",
    },
    "youtube_shorts": {
        "label": "YouTube Shorts",
        "description": "Vertical shorts (15-60s, 9:16)",
        "min_clip_duration": 15,
        "max_clip_duration": 60,
        "default_aspect_ratio": "9:16",
    },
    "instagram": {
        "label": "Instagram",
        "description": "Longer vertical clips (30-90s, 9:16)",
        "min_clip_duration": 30,
        "max_clip_duration": 90,
        "default_aspect_ratio": "9:16",
    },
    "youtube": {
        "label": "YouTube (landscape)",
        "description": "Traditional horizontal clips (60-180s, 16:9)",
        "min_clip_duration": 60,
        "max_clip_duration": 180,
        "default_aspect_ratio": "16:9",
    },
    "custom": {
        "label": "Custom",
        "description": "Set your own duration and aspect ratio",
        "min_clip_duration": 30,
        "max_clip_duration": 90,
        "default_aspect_ratio": "",
    },
}

# Descripciones de presets de subtitulos
SUBTITLE_PRESET_INFO: Dict[str, str] = {
    "default": "Clean white text with outline",
    "bold": "Bold white text, high visibility",
    "yellow": "Classic yellow subtitles",
    "tiktok": "TikTok-style centered captions",
    "small": "Smaller, unobtrusive text",
    "tiny": "Minimal, very small text",
}


class SetupWizardModal(ModalScreen[Optional[Dict[str, object]]]):
    """
    Modal de configuración inicial con pasos guiados.
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
    ]

    CSS = """
    SetupWizardModal {
        align: center middle;
    }

    #wizard_modal {
        width: 80%;
        max-width: 90;
        height: auto;
        max-height: 85%;
        background: $surface;
        border: heavy $primary;
        padding: 1 2;
    }

    #wizard_title {
        text-style: bold;
        text-align: center;
        padding: 1 0;
        color: $primary;
    }

    #wizard_subtitle {
        text-align: center;
        color: $text 70%;
        margin-bottom: 1;
    }

    .wizard-step {
        padding: 1 1;
        height: auto;
    }

    .step-header {
        text-style: bold;
        margin-bottom: 1;
    }

    .step-description {
        color: $text 80%;
        margin-bottom: 1;
    }

    .option-button {
        margin: 0 1 1 0;
        min-width: 20;
    }

    .option-button.selected {
        background: $primary 30%;
        border: solid $primary;
    }

    .options-grid {
        height: auto;
        layout: grid;
        grid-size: 2;
        grid-gutter: 1;
        padding: 1 0;
    }

    .option-card {
        height: auto;
        padding: 1;
        border: solid $panel;
        background: $surface;
    }

    .option-card.selected {
        border: solid $primary;
        background: $primary 15%;
    }

    .option-card:hover {
        background: $primary 10%;
    }

    .option-title {
        text-style: bold;
    }

    .option-desc {
        color: $text 70%;
    }

    #wizard_nav {
        dock: bottom;
        height: 3;
        padding: 1 0 0 0;
        border-top: solid $panel;
    }

    #step_indicator {
        text-align: center;
        color: $text 60%;
        width: 1fr;
    }

    #btn_back {
        min-width: 12;
    }

    #btn_next {
        min-width: 12;
    }

    .field-row {
        height: auto;
        margin: 1 0;
    }

    .field-label {
        text-style: bold;
        margin-bottom: 0;
    }

    .field-hint {
        color: $text 60%;
        margin-bottom: 0;
    }

    .field-error {
        color: $error;
        margin-top: 0;
    }

    #wizard_modal Input {
        margin: 0;
    }

    .custom-fields {
        margin-top: 1;
        padding: 1;
        border: dashed $panel;
        height: auto;
    }

    .custom-fields.hidden {
        display: none;
    }
    """

    def __init__(self, *, state_manager):
        super().__init__()
        self._state_manager = state_manager
        self._current_step = 0
        self._total_steps = 4

        # Collected settings
        self._settings: Dict[str, object] = {}

        # Step-specific state
        self._selected_platform: str = "tiktok"
        self._selected_subtitle_preset: str = "default"
        self._logo_error: str = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="wizard_modal"):
            yield Static("CLIPER Setup Wizard", id="wizard_title")
            yield Static("Configure your preferences", id="wizard_subtitle")

            # Step container - content changes based on current step
            with Vertical(id="wizard_content", classes="wizard-step"):
                yield from self._compose_current_step()

            # Navigation bar
            with Horizontal(id="wizard_nav"):
                yield Button("Back", id="btn_back", variant="default")
                yield Static("", id="step_indicator")
                yield Button("Next", id="btn_next", variant="primary")

    def _compose_current_step(self) -> ComposeResult:
        if self._current_step == 0:
            yield from self._compose_step_welcome()
        elif self._current_step == 1:
            yield from self._compose_step_branding()
        elif self._current_step == 2:
            yield from self._compose_step_platform()
        elif self._current_step == 3:
            yield from self._compose_step_subtitles()

    def _compose_step_welcome(self) -> ComposeResult:
        yield Static("Welcome to CLIPER!", classes="step-header")
        yield Static(
            "This wizard will help you configure the essential settings "
            "for generating social media clips from your videos.",
            classes="step-description",
        )
        yield Static("")
        yield Static("We'll set up:", classes="field-label")
        yield Static("  1. Your logo/watermark")
        yield Static("  2. Target platform (TikTok, YouTube, etc.)")
        yield Static("  3. Subtitle style")
        yield Static("")
        yield Static(
            "You can always change these later in Settings.",
            classes="field-hint",
        )

    def _compose_step_branding(self) -> ComposeResult:
        yield Static("Logo / Watermark", classes="step-header")
        yield Static(
            "Add your logo to exported clips. Leave as default to use the built-in logo, "
            "or enter a path to your own PNG/JPG file.",
            classes="step-description",
        )

        with Vertical(classes="field-row"):
            yield Static("Logo file path:", classes="field-label")
            current = self._settings.get("logo_path", "assets/logo.png")
            yield Input(
                placeholder="assets/logo.png or /path/to/logo.png",
                value=str(current),
                id="input_logo_path",
            )
            yield Static("", id="logo_error", classes="field-error")

        yield Static("")
        yield Static(
            "Tip: Use a PNG with transparency for best results.",
            classes="field-hint",
        )

    def _compose_step_platform(self) -> ComposeResult:
        yield Static("Target Platform", classes="step-header")
        yield Static(
            "Select your primary platform to optimize clip duration and aspect ratio.",
            classes="step-description",
        )

        with Vertical(classes="options-grid"):
            for key, preset in PLATFORM_PRESETS.items():
                selected = "selected" if key == self._selected_platform else ""
                with Vertical(classes=f"option-card {selected}", id=f"platform_{key}"):
                    yield Static(str(preset["label"]), classes="option-title")
                    yield Static(str(preset["description"]), classes="option-desc")

        # Custom fields (shown when "custom" is selected)
        hidden = "" if self._selected_platform == "custom" else "hidden"
        with Vertical(classes=f"custom-fields {hidden}", id="custom_fields"):
            yield Static("Custom Settings:", classes="field-label")
            with Horizontal(classes="field-row"):
                yield Static("Min duration (s):", classes="field-hint")
                yield Input(
                    value=str(self._settings.get("min_clip_duration", 30)),
                    id="input_min_duration",
                )
            with Horizontal(classes="field-row"):
                yield Static("Max duration (s):", classes="field-hint")
                yield Input(
                    value=str(self._settings.get("max_clip_duration", 90)),
                    id="input_max_duration",
                )
            with Horizontal(classes="field-row"):
                yield Static("Aspect ratio:", classes="field-hint")
                yield Input(
                    placeholder="9:16, 16:9, 1:1, or blank",
                    value=str(self._settings.get("default_aspect_ratio", "")),
                    id="input_aspect_ratio",
                )

    def _compose_step_subtitles(self) -> ComposeResult:
        yield Static("Subtitle Style", classes="step-header")
        yield Static(
            "Choose a subtitle preset for your exported clips.",
            classes="step-description",
        )

        with Vertical(classes="options-grid"):
            for preset in sorted(SUBTITLE_PRESETS):
                selected = "selected" if preset == self._selected_subtitle_preset else ""
                desc = SUBTITLE_PRESET_INFO.get(preset, "")
                with Vertical(classes=f"option-card {selected}", id=f"subtitle_{preset}"):
                    yield Static(preset.capitalize(), classes="option-title")
                    yield Static(desc, classes="option-desc")

    def on_mount(self) -> None:
        self._update_navigation()
        # Load current settings as defaults
        self._settings["logo_path"] = self._state_manager.get_setting("logo_path", "assets/logo.png")
        self._settings["min_clip_duration"] = self._state_manager.get_setting("min_clip_duration", 30)
        self._settings["max_clip_duration"] = self._state_manager.get_setting("max_clip_duration", 90)
        self._settings["default_aspect_ratio"] = self._state_manager.get_setting("default_aspect_ratio", "")
        self._settings["subtitle_preset"] = self._state_manager.get_setting("subtitle_preset", "default")
        self._selected_subtitle_preset = str(self._settings.get("subtitle_preset", "default"))

    def _update_navigation(self) -> None:
        """Update navigation buttons and step indicator."""
        try:
            btn_back = self.query_one("#btn_back", Button)
            btn_next = self.query_one("#btn_next", Button)
            indicator = self.query_one("#step_indicator", Static)

            # Back button
            btn_back.disabled = self._current_step == 0

            # Next button label
            if self._current_step == self._total_steps - 1:
                btn_next.label = "Finish"
            else:
                btn_next.label = "Next"

            # Step indicator
            indicator.update(f"Step {self._current_step + 1} of {self._total_steps}")
        except Exception:
            pass

    def _refresh_step_content(self) -> None:
        """Refresh the wizard content for the current step."""
        try:
            content = self.query_one("#wizard_content", Vertical)
            content.remove_children()
            for widget in self._compose_current_step():
                content.mount(widget)
            self._update_navigation()
        except Exception:
            pass

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "btn_back":
            if self._current_step > 0:
                self._collect_current_step_data()
                self._current_step -= 1
                self._refresh_step_content()
            return

        if button_id == "btn_next":
            if not self._validate_current_step():
                return
            self._collect_current_step_data()

            if self._current_step < self._total_steps - 1:
                self._current_step += 1
                self._refresh_step_content()
            else:
                # Finish - save all settings
                self._save_all_settings()
                self.dismiss({"completed": True, "settings": dict(self._settings)})
            return

        # Handle option card clicks (platform selection)
        if button_id and button_id.startswith("platform_"):
            platform_key = button_id.replace("platform_", "")
            self._select_platform(platform_key)
            return

        # Handle subtitle preset clicks
        if button_id and button_id.startswith("subtitle_"):
            preset_key = button_id.replace("subtitle_", "")
            self._select_subtitle_preset(preset_key)
            return

    def on_click(self, event) -> None:
        """Handle clicks on option cards."""
        # Find if click was inside an option card
        widget = event.widget
        while widget is not None:
            widget_id = getattr(widget, "id", None)
            if widget_id:
                if widget_id.startswith("platform_"):
                    platform_key = widget_id.replace("platform_", "")
                    self._select_platform(platform_key)
                    return
                if widget_id.startswith("subtitle_"):
                    preset_key = widget_id.replace("subtitle_", "")
                    self._select_subtitle_preset(preset_key)
                    return
            widget = getattr(widget, "parent", None)

    def _select_platform(self, platform_key: str) -> None:
        """Select a platform preset."""
        if platform_key not in PLATFORM_PRESETS:
            return

        self._selected_platform = platform_key
        preset = PLATFORM_PRESETS[platform_key]

        # Update settings from preset
        if platform_key != "custom":
            self._settings["min_clip_duration"] = preset["min_clip_duration"]
            self._settings["max_clip_duration"] = preset["max_clip_duration"]
            self._settings["default_aspect_ratio"] = preset["default_aspect_ratio"]

        # Refresh to show selection
        self._refresh_step_content()

    def _select_subtitle_preset(self, preset_key: str) -> None:
        """Select a subtitle preset."""
        if preset_key not in SUBTITLE_PRESETS:
            return

        self._selected_subtitle_preset = preset_key
        self._settings["subtitle_preset"] = preset_key
        self._settings["subtitle_style_mode"] = "preset"

        # Refresh to show selection
        self._refresh_step_content()

    def _validate_current_step(self) -> bool:
        """Validate the current step before proceeding."""
        if self._current_step == 1:  # Branding step
            return self._validate_logo_path()
        if self._current_step == 2:  # Platform step (custom mode)
            if self._selected_platform == "custom":
                return self._validate_custom_platform()
        return True

    def _validate_logo_path(self) -> bool:
        """Validate the logo path input."""
        try:
            input_widget = self.query_one("#input_logo_path", Input)
            error_widget = self.query_one("#logo_error", Static)
        except Exception:
            return True

        path = input_widget.value.strip()
        if not path:
            path = "assets/logo.png"

        # Validate using the logo utility
        try:
            from src.utils.logo import coerce_logo_file
            result = coerce_logo_file(path)
            if result is None:
                error_widget.update("Logo file not found or invalid format")
                return False
            error_widget.update("")
            return True
        except Exception as e:
            error_widget.update(str(e))
            return False

    def _validate_custom_platform(self) -> bool:
        """Validate custom platform settings."""
        try:
            min_input = self.query_one("#input_min_duration", Input)
            max_input = self.query_one("#input_max_duration", Input)

            min_val = int(min_input.value.strip() or "30")
            max_val = int(max_input.value.strip() or "90")

            if min_val < 1:
                return False
            if max_val < min_val:
                return False
            return True
        except (ValueError, Exception):
            return False

    def _collect_current_step_data(self) -> None:
        """Collect data from the current step."""
        if self._current_step == 1:  # Branding
            try:
                input_widget = self.query_one("#input_logo_path", Input)
                path = input_widget.value.strip() or "assets/logo.png"
                self._settings["logo_path"] = path
            except Exception:
                pass

        elif self._current_step == 2:  # Platform
            if self._selected_platform == "custom":
                try:
                    min_input = self.query_one("#input_min_duration", Input)
                    max_input = self.query_one("#input_max_duration", Input)
                    aspect_input = self.query_one("#input_aspect_ratio", Input)

                    self._settings["min_clip_duration"] = int(min_input.value.strip() or "30")
                    self._settings["max_clip_duration"] = int(max_input.value.strip() or "90")
                    self._settings["default_aspect_ratio"] = aspect_input.value.strip()
                except Exception:
                    pass

        elif self._current_step == 3:  # Subtitles
            self._settings["subtitle_preset"] = self._selected_subtitle_preset
            self._settings["subtitle_style_mode"] = "preset"

    def _save_all_settings(self) -> None:
        """Save all collected settings to state manager."""
        for key, value in self._settings.items():
            try:
                self._state_manager.set_setting(key, value)
            except Exception:
                pass  # Skip invalid settings

        # Mark wizard as completed
        self._state_manager.set_setting("_wizard_completed", True)
