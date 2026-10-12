"""User configuration: one TOML file, defaults merged in, unknown keys warned about."""

from __future__ import annotations

import re
import tomllib
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

import tomli_w

from wowfish import paths

DEFAULT_CONFIG_TEXT = """# wowfish configuration. Delete any line to go back to its default.

[game]
# Keybind for the Fishing ability on your action bar.
cast_key = "1"
# Stop fishing after this many minutes.
session_minutes = 60

[models]
# Development only: override the model revision pinned into this build.
# revision = "main"
"""

_LINE_RE = re.compile(r"\(at line (\d+), column \d+\)")
# Commit hashes, tags, and simple branch names. Used as a path component, so no separators.
_REVISION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ConfigError(Exception):
    def __init__(self, path: Path, message: str, line: int | None = None) -> None:
        self.path = path
        self.message = message
        self.line = line
        super().__init__(str(self))

    def __str__(self) -> str:
        where = f"{self.path} line {self.line}" if self.line is not None else str(self.path)
        return f"Config error in {where}: {self.message}"


@dataclass(frozen=True)
class GameConfig:
    cast_key: str = "1"
    session_minutes: int = 60


@dataclass(frozen=True)
class ModelsConfig:
    revision: str | None = None


@dataclass(frozen=True)
class Config:
    game: GameConfig
    models: ModelsConfig


_SECTIONS: dict[str, type] = {"game": GameConfig, "models": ModelsConfig}


def ensure_config_file(path: Path | None = None) -> bool:
    path = path or paths.config_file()
    if path.exists():
        return False
    path.write_text(DEFAULT_CONFIG_TEXT)
    return True


def load_config(path: Path | None = None) -> tuple[Config, list[str]]:
    path = path or paths.config_file()
    if not path.exists():
        return Config(game=GameConfig(), models=ModelsConfig()), []
    try:
        raw = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        m = _LINE_RE.search(str(e))
        raise ConfigError(path, str(e), int(m.group(1)) if m else None) from e

    warnings: list[str] = []
    built: dict[str, Any] = {}
    for section, cls in _SECTIONS.items():
        table = raw.pop(section, {})
        if not isinstance(table, dict):
            raise ConfigError(path, f"[{section}] must be a table")
        built[section] = _build_section(path, section, cls, table, warnings)
    for leftover in raw:
        warnings.append(f"unknown section [{leftover}] ignored")
    cfg = Config(**built)
    rev = cfg.models.revision
    if rev is not None and not _REVISION_RE.match(rev):
        raise ConfigError(
            path, f"models.revision must be a commit hash, tag, or simple branch name, got {rev!r}"
        )
    return cfg, warnings


def _build_section(
    path: Path, section: str, cls: type, table: dict[str, Any], warnings: list[str]
) -> Any:
    known = {f.name: f for f in fields(cls)}
    kwargs: dict[str, Any] = {}
    for key, value in table.items():
        if key not in known:
            warnings.append(f"unknown key {section}.{key} ignored")
            continue
        expected = _expected_type(known[key].type)
        if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
            raise ConfigError(
                path, f"{section}.{key} must be {expected.__name__}, got {type(value).__name__}"
            )
        kwargs[key] = value
    return cls(**kwargs)


def _expected_type(annotation: Any) -> type:
    # Annotations are strings because of `from __future__ import annotations`.
    text = annotation if isinstance(annotation, str) else getattr(annotation, "__name__", "")
    base = text.replace(" | None", "").strip()
    return {"str": str, "int": int, "bool": bool, "float": float}[base]


def to_toml(cfg: Config) -> str:
    data = asdict(cfg)
    data["models"] = {k: v for k, v in data["models"].items() if v is not None}
    return tomli_w.dumps(data)
