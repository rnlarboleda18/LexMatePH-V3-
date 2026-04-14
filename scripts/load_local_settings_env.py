"""
Merge `local.settings.json` → `Values` into `os.environ` for keys not already set.

Reads, in order (each file only fills *missing* env vars):
  1. `<repo>/api/local.settings.json` — Azure Functions default location
  2. `<repo>/local.settings.json` — repo root (also gitignored)

Used by maintenance scripts so Option A works without exporting variables in the shell.
Never commit real secrets; these paths are in `.gitignore`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def _merge_values_file(path: Path) -> None:
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    vals = data.get("Values") or {}
    if not isinstance(vals, dict):
        return
    for key, value in vals.items():
        if value is None or value == "":
            continue
        if not os.environ.get(key):
            os.environ[key] = str(value)


def load_api_local_settings_into_environ(repo_root: Path | None = None) -> None:
    root = repo_root if repo_root is not None else Path(__file__).resolve().parents[1]
    _merge_values_file(root / "api" / "local.settings.json")
    _merge_values_file(root / "local.settings.json")
