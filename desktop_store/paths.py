from __future__ import annotations

import os
import sys
from pathlib import Path


def app_data_dir() -> Path:
    if sys.platform == "win32":
        root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(root) / "DesktopStore"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "DesktopStore"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "desktop-store"
    return Path.home() / ".local" / "share" / "desktop-store"


def db_path() -> Path:
    override = os.environ.get("DESKTOP_STORE_DB")
    if override:
        return Path(override)
    return app_data_dir() / "store.db"


def images_dir() -> Path:
    return app_data_dir() / "images"
