"""Where wowfish keeps its files.

Set WOWFISH_HOME to put everything under one directory (used by tests and CI).
Otherwise follow the OS convention via platformdirs.
"""

from __future__ import annotations

import os
from pathlib import Path

import platformdirs

APP_NAME = "wowfish"


def _home() -> Path | None:
    raw = os.environ.get("WOWFISH_HOME")
    return Path(raw).expanduser() if raw else None


def _ensure(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_dir() -> Path:
    home = _home()
    return _ensure(home / "config" if home else Path(platformdirs.user_config_dir(APP_NAME)))


def cache_dir() -> Path:
    home = _home()
    return _ensure(home / "cache" if home else Path(platformdirs.user_cache_dir(APP_NAME)))


def log_dir() -> Path:
    home = _home()
    return _ensure(home / "log" if home else Path(platformdirs.user_log_dir(APP_NAME)))


def config_file() -> Path:
    return config_dir() / "config.toml"


def models_dir() -> Path:
    return _ensure(cache_dir() / "models")


def log_file() -> Path:
    return log_dir() / "wowfish.log"
