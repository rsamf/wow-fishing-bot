"""Environment probes behind `wowfish doctor`. Probes never raise; failures become lines."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from wowfish import __version__, paths

Level = Literal["ok", "warn", "fail"]


@dataclass(frozen=True)
class ProbeResult:
    name: str
    level: Level
    detail: str


Probe = Callable[[], ProbeResult]


def run_probes(probes: Sequence[Probe]) -> list[ProbeResult]:
    results: list[ProbeResult] = []
    for probe in probes:
        try:
            results.append(probe())
        except Exception as e:  # doctor must never crash
            results.append(ProbeResult(probe.__name__, "fail", f"{type(e).__name__}: {e}"))
    return results


def render(results: Sequence[ProbeResult]) -> str:
    return "\n".join(f"{r.level:<5} {r.name}: {r.detail}" for r in results)


def exit_code(results: Sequence[ProbeResult]) -> int:
    return 1 if any(r.level == "fail" for r in results) else 0


# ---- probes -------------------------------------------------------------------


def probe_system() -> ProbeResult:
    detail = (
        f"{platform.system()} {platform.machine()}, "
        f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}, "
        f"wowfish {__version__}, log {paths.log_file()}"
    )
    return ProbeResult("system", "ok", detail)


def _screencast_portal_available() -> bool:
    """True if org.freedesktop.portal.ScreenCast answers on the session bus."""
    tool = shutil.which("busctl")
    if not tool:
        return False
    try:
        proc = subprocess.run(
            [
                tool,
                "--user",
                "introspect",
                "org.freedesktop.portal.Desktop",
                "/org/freedesktop/portal/desktop",
                "org.freedesktop.portal.ScreenCast",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0 and "CreateSession" in proc.stdout


def probe_display() -> ProbeResult:
    if sys.platform != "linux":
        return ProbeResult("display", "ok", "native")
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session == "wayland" or (not session and os.environ.get("WAYLAND_DISPLAY")):
        if _screencast_portal_available():
            return ProbeResult("display", "ok", "wayland (ScreenCast portal available)")
        return ProbeResult("display", "warn", "wayland, ScreenCast portal not reachable")
    if session == "x11" or os.environ.get("DISPLAY"):
        return ProbeResult("display", "ok", "x11")
    return ProbeResult("display", "warn", "none")


def probe_onnxruntime() -> ProbeResult:
    import onnxruntime

    providers = onnxruntime.get_available_providers()
    detail = f"{onnxruntime.__version__}, providers: {', '.join(providers)}"
    if "CPUExecutionProvider" not in providers:
        return ProbeResult("onnxruntime", "fail", f"CPUExecutionProvider missing ({detail})")
    return ProbeResult("onnxruntime", "ok", detail)


def probe_game_window() -> ProbeResult:
    # Window discovery lands with the bot runtime. The line exists so reports have a stable shape.
    return ProbeResult("game window", "warn", "not found (window discovery not implemented yet)")


def probe_models() -> ProbeResult:
    from wowfish import models
    from wowfish.config import ConfigError, load_config

    try:
        cfg, _ = load_config()
    except ConfigError:
        cfg = None
    revision = models.effective_revision(cfg) if cfg else models.MODEL_REVISION
    note = " (override from config)" if cfg and cfg.models.revision else ""
    statuses = models.status(revision)
    missing = [s.spec.filename for s in statuses if not s.cached]
    if missing:
        return ProbeResult(
            "models", "warn", f"{', '.join(missing)} not downloaded, run `wowfish models pull`"
        )
    return ProbeResult("models", "ok", f"{len(statuses)} cached at {revision}{note}")


def probe_config() -> ProbeResult:
    from wowfish.config import ConfigError, load_config

    path = paths.config_file()
    try:
        _, warnings = load_config(path)
    except ConfigError as e:
        return ProbeResult("config", "fail", str(e))
    if warnings:
        return ProbeResult("config", "warn", f"{path}: " + "; ".join(warnings))
    return ProbeResult("config", "ok", str(path) if path.exists() else f"{path} (defaults)")


def default_probes() -> list[Probe]:
    return [
        probe_system,
        probe_display,
        probe_onnxruntime,
        probe_game_window,
        probe_models,
        probe_config,
    ]
