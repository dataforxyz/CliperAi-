# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Type, TypeVar

T = TypeVar("T")


def _validate_type(value: Any, expected_type: Type[T]) -> T:
    """
    Small compatibility wrapper for pydantic v1/v2 typed validation.
    """
    try:
        from pydantic import TypeAdapter  # type: ignore
    except (ModuleNotFoundError, ImportError):
        TypeAdapter = None  # type: ignore[assignment]

    if TypeAdapter is not None:
        try:
            return TypeAdapter(expected_type).validate_python(value)  # type: ignore[no-any-return]
        except Exception as e:
            msg = str(e).strip() or "Invalid value"
            raise ValueError(msg) from None

    try:
        from pydantic import parse_obj_as  # type: ignore
    except (ModuleNotFoundError, ImportError):
        parse_obj_as = None  # type: ignore[assignment]

    if parse_obj_as is not None:
        try:
            return parse_obj_as(expected_type, value)  # type: ignore[no-any-return]
        except Exception as e:
            msg = str(e).strip() or "Invalid value"
            raise ValueError(msg) from None

    # Fallback when pydantic isn't available (e.g., minimal TUI env).
    if expected_type is str:
        return ("" if value is None else str(value))  # type: ignore[return-value]
    if expected_type is bool:
        if isinstance(value, bool):
            return value  # type: ignore[return-value]
        if value is None:
            return False  # type: ignore[return-value]
        if isinstance(value, (int, float)):
            return bool(value)  # type: ignore[return-value]
        lowered = str(value).strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True  # type: ignore[return-value]
        if lowered in {"0", "false", "no", "n", "off", ""}:
            return False  # type: ignore[return-value]
        raise ValueError(f"Invalid boolean value: {value!r}")
    if expected_type is int:
        return int(value)  # type: ignore[return-value]
    if expected_type is float:
        return float(value)  # type: ignore[return-value]
    if isinstance(value, expected_type):
        return value  # type: ignore[return-value]
    raise ValueError(f"Expected {expected_type.__name__}, got {type(value).__name__}")


@dataclass(frozen=True)
class SettingGroup:
    key: str
    title: str
    description: str = ""


@dataclass(frozen=True)
class SettingDefinition:
    key: str
    group: str
    label: str
    python_type: Type[Any]
    default: Any
    help_text: str = ""
    placeholder: str = ""
    is_secret: bool = False
    normalize: Optional[Callable[[Any], Any]] = None

    def validate_and_normalize(self, value: Any) -> Any:
        typed = _validate_type(value, self.python_type)
        if self.normalize is None:
            return typed
        return self.normalize(typed)

    def validate_from_text(self, raw: str) -> Any:
        text = "" if raw is None else str(raw)
        if self.python_type is str:
            return self.validate_and_normalize(text)

        stripped = text.strip()
        if stripped == "":
            return self.validate_and_normalize(self.default)

        if self.python_type is bool:
            lowered = stripped.lower()
            if lowered in {"1", "true", "yes", "y", "on"}:
                return self.validate_and_normalize(True)
            if lowered in {"0", "false", "no", "n", "off"}:
                return self.validate_and_normalize(False)
            raise ValueError("Must be a boolean (true/false)")

        if self.python_type is int:
            try:
                return self.validate_and_normalize(int(stripped))
            except ValueError as e:
                raise ValueError("Must be an integer") from e

        if self.python_type is float:
            try:
                return self.validate_and_normalize(float(stripped))
            except ValueError as e:
                raise ValueError("Must be a number") from e

        return self.validate_and_normalize(stripped)


def _normalize_logo_path(value: str) -> str:
    from src.utils.logo import DEFAULT_BUILTIN_LOGO_PATH, is_valid_logo_location, normalize_logo_setting_value

    candidate = (value or "").strip() or DEFAULT_BUILTIN_LOGO_PATH
    if not is_valid_logo_location(candidate):
        raise ValueError("Must be an existing image file or a directory containing logo.{png,jpg,jpeg,webp}")
    return normalize_logo_setting_value(candidate)


APP_SETTING_GROUPS: Tuple[SettingGroup, ...] = (
    SettingGroup(key="branding", title="Branding", description="Defaults used by export workflows."),
)


APP_SETTINGS: Tuple[SettingDefinition, ...] = (
    SettingDefinition(
        key="logo_path",
        group="branding",
        label="Logo path (file or directory):",
        python_type=str,
        default="assets/logo.png",
        placeholder="assets/logo.png",
        help_text="Used for video watermarking where supported.",
        normalize=_normalize_logo_path,
    ),
)


def iter_app_setting_groups() -> Sequence[SettingGroup]:
    return list(APP_SETTING_GROUPS)


def iter_app_settings() -> Sequence[SettingDefinition]:
    return list(APP_SETTINGS)


def get_app_setting_definition(key: str) -> Optional[SettingDefinition]:
    for setting in APP_SETTINGS:
        if setting.key == key:
            return setting
    return None


def get_app_settings_defaults() -> Dict[str, Any]:
    return {s.key: s.default for s in APP_SETTINGS}


def validate_and_normalize_app_settings(settings: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Validates known keys and returns:
    - validated settings dict with schema defaults merged
    - per-key error strings for any invalid persisted values

    Unknown keys are preserved as-is.
    """
    merged: Dict[str, Any] = dict(get_app_settings_defaults())
    merged.update(settings or {})

    errors: Dict[str, str] = {}
    for definition in APP_SETTINGS:
        if definition.key not in merged:
            merged[definition.key] = definition.default
            continue
        try:
            merged[definition.key] = definition.validate_and_normalize(merged.get(definition.key))
        except Exception as e:
            errors[definition.key] = str(e).strip() or "Invalid value"
            merged[definition.key] = definition.default
    return merged, errors


def list_app_settings_by_group() -> Dict[str, List[SettingDefinition]]:
    grouped: Dict[str, List[SettingDefinition]] = {}
    for definition in APP_SETTINGS:
        grouped.setdefault(definition.group, []).append(definition)
    return grouped
