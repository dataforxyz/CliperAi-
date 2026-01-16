from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Union

PathLike = Union[str, Path]


def open_path(path: PathLike) -> None:
    target = Path(path).expanduser()
    if not target.exists():
        raise FileNotFoundError(f"Path does not exist: {target}")
    target = target.resolve()

    if sys.platform.startswith("win"):
        os.startfile(str(target))  # type: ignore[attr-defined]
        return

    if sys.platform == "darwin":
        _run_open_cmd(["open", "--", str(target)])
        return

    opener = shutil.which("xdg-open")
    if not opener:
        raise RuntimeError(
            "xdg-open not found; install xdg-utils to enable opening files/folders."
        )
    _run_open_cmd([opener, str(target)])


def _run_open_cmd(cmd: list[str]) -> None:
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except Exception as e:
        raise RuntimeError(f"Failed to run open command: {cmd}: {e}") from e
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        details = stderr or stdout or f"exit code {result.returncode}"
        raise RuntimeError(f"Open command failed: {cmd}: {details}")
