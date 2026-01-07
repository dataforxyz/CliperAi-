import asyncio
import json
from pathlib import Path

import pytest

pytest.importorskip("textual")


async def _wait_until(pilot, predicate, *, timeout: float = 5.0, step: float = 0.05) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        if predicate():
            return
        if loop.time() >= deadline:
            raise AssertionError("Timed out waiting for UI state")
        await pilot.pause(step)


def test_settings_modal_layout_common_sizes(tmp_path: Path, monkeypatch) -> None:
    async def run(size: tuple[int, int]) -> None:
        monkeypatch.chdir(tmp_path)

        import src.utils.state_manager as state_manager_module

        state_manager_module._state_manager_instance = None
        settings_file = tmp_path / "config" / "app_settings.json"
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        # Pre-set wizard_completed to skip the setup wizard during tests
        settings_file.write_text(json.dumps({"_wizard_completed": True}), encoding="utf-8")
        state_manager_module._state_manager_init_kwargs = {"app_root": tmp_path, "settings_file": settings_file}

        import src.tui.app as tui_app_module

        app = tui_app_module.CliperTUI()

        async with app.run_test(size=size) as pilot:
            from textual.widgets import Button, Input, Static

            await pilot.press("s")

            def has_logo_input() -> bool:
                try:
                    app.screen.query_one("#setting_logo_path", Input)
                    return True
                except Exception:
                    return False

            await _wait_until(pilot, has_logo_input)

            # Invalid extension: should show a clear error + disable Save.
            invalid_logo = tmp_path / "logo.gif"
            invalid_logo.write_bytes(b"")
            app.screen.query_one("#setting_logo_path", Input).value = str(invalid_logo)
            # Force a validation pass (programmatic value changes may not emit Input.Changed).
            app.screen.query_one("#save", Button).press()

            def save_disabled_with_error() -> bool:
                try:
                    err = app.screen.query_one("#setting_logo_path_error", Static)
                    save = app.screen.query_one("#save", Button)
                    return bool(save.disabled) and bool(err.display) and bool(str(getattr(err, "content", "")).strip())
                except Exception:
                    return False

            await _wait_until(pilot, save_disabled_with_error)

            # Valid PNG: should enable Save and persist.
            custom_logo = tmp_path / "logo.png"
            custom_logo.write_bytes(b"\x89PNG\r\n\x1a\n")
            app.screen.query_one("#setting_logo_path", Input).value = str(custom_logo)
            await _wait_until(pilot, lambda: not app.screen.query_one("#save", Button).disabled)
            app.screen.query_one("#save", Button).press()

            await _wait_until(pilot, lambda: not has_logo_input())

            persisted = json.loads(settings_file.read_text(encoding="utf-8"))
            assert persisted.get("logo_path") == str(custom_logo)

    # Smoke-check common terminal sizes for the new modal layout.
    for size in [(80, 24), (100, 30), (120, 40)]:
        asyncio.run(run(size))
