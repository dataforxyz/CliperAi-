# App Config & Settings

This project stores **global app settings** (defaults used across runs) in `config/app_settings.json`. These settings are:

- Defined in one canonical place: `src/config/settings_schema.py`
- Persisted and validated by: `src/utils/state_manager.py`
- Rendered in the Textual TUI Settings modal from the same schema: `src/tui/app.py` (`SettingsModal`)

## Where settings live

### Canonical definition (single source of truth)

`src/config/settings_schema.py` defines:

- Groups (`APP_SETTING_GROUPS`)
- Settings (`APP_SETTINGS`) with:
  - `key` (persisted JSON key)
  - `group` (for UI grouping)
  - `label`, `help_text`, `placeholder` (UI text)
  - `python_type` (type validation)
  - `default`
  - `normalize` hook (validation/normalization; raise `ValueError` on invalid)

### Persistence format

`config/app_settings.json` is a free-form JSON object (dict). Known keys are validated/normalized; unknown keys are preserved.

## How to add a new setting (end-to-end)

### 1) Add it to the schema

Edit `src/config/settings_schema.py`:

1. Pick an existing group in `APP_SETTING_GROUPS` (or add a new `SettingGroup`).
2. Add a `SettingDefinition` entry in `APP_SETTINGS`.

Example (string setting with normalization):

```py
def _normalize_example_path(value: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        raise ValueError("Path cannot be empty")
    return candidate

APP_SETTINGS = (
    # ...
    SettingDefinition(
        key="example_path",
        group="branding",
        label="Example path:",
        python_type=str,
        default="",
        placeholder="/path/to/example",
        help_text="Used by the example feature.",
        normalize=_normalize_example_path,
    ),
)
```

Notes:

- `key` becomes the persisted JSON key and the deterministic TUI widget id: `setting_<key>`.
- `normalize` should both validate and normalize (e.g., expand/resolve paths) and should raise `ValueError` with a user-friendly message on invalid input.

### 2) Defaults and persistence happen automatically

No extra wiring is required:

- On startup, `StateManager` merges defaults from the schema into the loaded `config/app_settings.json`.
- Known keys are validated/normalized; invalid values are reset to defaults and logged.

### 3) The TUI renders it automatically

No TUI code changes are required:

- `SettingsModal` reads groups + settings from `src/config/settings_schema.py`.
- It renders label/help/default and an `Input` with id `setting_<key>` plus an error line `setting_<key>_error`.
- Save is disabled until all schema-defined fields validate.

### 4) Reading/writing in code

Use `StateManager`:

```py
value = state_manager.get_setting("example_path")
state_manager.set_setting("example_path", "/new/value")
```

For schema-defined keys, `set_setting` validates/normalizes before persisting.

## Existing settings

- `logo_path`: Default logo location for export workflows (validated/normalized via `src/utils/logo.py`).

