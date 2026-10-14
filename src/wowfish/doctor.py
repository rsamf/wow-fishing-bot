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


def probe_opencv() -> ProbeResult:
    import cv2

    return ProbeResult("opencv", "ok", cv2.__version__)


def probe_audio() -> ProbeResult:
    from wowfish.audio import AudioUnavailable, devices

    try:
        found = devices.list_loopback_devices()
    except AudioUnavailable as e:
        return ProbeResult("audio", "warn", f"no audio backend ({e})")
    if not found:
        return ProbeResult(
            "audio",
            "warn",
            "no loopback devices (macOS: install a virtual device such as BlackHole)",
        )
    default = next((d.name for d in found if d.is_default), found[0].name)
    return ProbeResult("audio", "ok", f"{len(found)} loopback device(s), default: {default}")


def probe_game_window() -> ProbeResult:
    # Window discovery lands with the bot runtime. The line exists so reports have a stable shape.
    return ProbeResult("game window", "warn", "not found (window discovery not implemented yet)")


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
        probe_opencv,
        probe_audio,
        probe_game_window,
        probe_config,
    ]
