"""Screen capture boundary. Real implementations arrive with the bot runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np


@dataclass(frozen=True)
class WindowRef:
    title: str
    pid: int | None
    left: int
    top: int
    width: int
    height: int


@runtime_checkable
class Capturer(Protocol):
    def open(self, window: WindowRef) -> None: ...

    def grab(self) -> np.ndarray:
        """Return the current frame as HxWx3 uint8 BGR."""
        ...

    def close(self) -> None: ...


def get_capturer() -> Capturer:
    from wowfish.capture._stub import StubCapturer

    return StubCapturer()


__all__ = ["Capturer", "WindowRef", "get_capturer"]
