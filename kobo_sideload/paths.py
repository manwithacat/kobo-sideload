"""Where the pipeline stores cache, payload, and distributable zips."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def default_home() -> Path:
    override = os.environ.get("KOBO_SIDELOAD_HOME")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "kobo-sideload"
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "kobo-sideload"
    xdg = os.environ.get("XDG_CACHE_HOME")
    cache = Path(xdg) if xdg else Path.home() / ".cache"
    return cache / "kobo-sideload"


def work_dirs(root: Path) -> dict[str, Path]:
    return {
        "work": root,
        "cache": root / "cache",
        "payload": root / "payload",
        "dist": root / "dist",
        "catalog": root / "catalog.json",
    }
