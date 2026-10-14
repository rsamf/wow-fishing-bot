"""Environment probes behind `wowfish doctor`. Probes never raise; failures become lines."""

from __future__ import annotations

import os
import platform
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from wowfish import __version__, paths
from wowfish.capture import find_window

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


def _x_display_opens() -> tuple[bool, str]:
    try:
        from Xlib import display

        display.Display().close()
        return True, ""
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def probe_display() -> ProbeResult:
    if sys.platform != "linux":
        return ProbeResult("display", "ok", "native")
    name = os.environ.get("DISPLAY")
    if not name:
        return ProbeResult(
            "display",
            "warn",
            "DISPLAY is not set; the bot needs X11 or Xwayland (log into a session with one)",
        )
    ok, why = _x_display_opens()
    if not ok:
        return ProbeResult("display", "fail", f"cannot open {name}: {why}")
    server = "Xwayland" if os.environ.get("WAYLAND_DISPLAY") else "X11"
    return ProbeResult("display", "ok", f"{name} ({server})")


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
    w = find_window("World of Warcraft")
    if w is None:
        return ProbeResult("game window", "warn", "not found; is the game running?")
    return ProbeResult(
        "game window", "ok", f"{w.title!r} {w.width}x{w.height} at +{w.left}+{w.top}"
    )


def _xtest_available() -> tuple[bool, str]:
    from wowfish.input._x11 import xtest_available

    return xtest_available()


def probe_input() -> ProbeResult:
    if sys.platform == "win32":
        return ProbeResult("input", "ok", "SendInput")
    if sys.platform == "linux" and os.environ.get("DISPLAY"):
        ok, detail = _xtest_available()
        return ProbeResult("input", "ok" if ok else "fail", detail)
    return ProbeResult("input", "warn", "key presses not supported yet on this platform")


def probe_calibration() -> ProbeResult:
    from wowfish.config import ConfigError, load_config
    from wowfish.vision.matcher import MIN_TEMPLATE_PX

    hint = (
        "run `wowfish calibrate --save` on a screenshot showing the gear icon (or the GUI's Setup)"
    )
    try:
        cfg, _ = load_config()
    except ConfigError as e:
        return ProbeResult("calibration", "fail", str(e))
    size = cfg.vision.icon_size_px
    if size <= 0:
        return ProbeResult("calibration", "warn", f"icon not calibrated; {hint}")
    w = find_window("World of Warcraft")
    if w is None:
        return ProbeResult("calibration", "warn", f"{size} px (no game window to check it against)")
    px = round(size * min(1.0, cfg.vision.match_width / w.width))
    if px < MIN_TEMPLATE_PX:
        return ProbeResult(
            "calibration",
            "fail",
            f"{size} px is {px} px after downscaling this {w.width}-wide window "
            f"(minimum {MIN_TEMPLATE_PX}); {hint}",
        )
    return ProbeResult("calibration", "ok", f"{size} px ({px} px in the matcher)")


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
        probe_input,
        probe_calibration,
        probe_config,
    ]
