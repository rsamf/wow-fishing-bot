"""Screen capture boundary: find the game window and grab its pixels as BGR arrays."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np

Box = tuple[int, int, int, int]  # x, y, width, height in window pixels


@dataclass(frozen=True)
class WindowRef:
    title: str
    pid: int | None
    left: int
    top: int
    width: int
    height: int
    handle: int | None = None  # native window id where the platform has one


@runtime_checkable
class Capturer(Protocol):
    def open(self, window: WindowRef) -> None: ...

    def grab(self, box: Box | None = None) -> np.ndarray:
        """Return the window (or `box` inside it) as HxWx3 uint8 BGR."""
        ...

    def close(self) -> None: ...


def _linux_x11() -> bool:
    return sys.platform == "linux" and bool(os.environ.get("DISPLAY"))


def find_window(title_substring: str = "World of Warcraft") -> WindowRef | None:
    """The largest viewable window whose title contains the text. Linux/X11 only for now."""
    if _linux_x11():
        from wowfish.capture._x11 import find_window_x11

        return find_window_x11(title_substring)
    return None


def get_capturer() -> Capturer:
    if _linux_x11():
        from wowfish.capture._x11 import X11WindowCapturer

        return X11WindowCapturer()
    try:
        import mss  # noqa: F401
    except Exception:
        from wowfish.capture._stub import StubCapturer

        return StubCapturer()
    from wowfish.capture._mss import MssCapturer

    return MssCapturer()


__all__ = ["Box", "Capturer", "WindowRef", "find_window", "get_capturer"]
