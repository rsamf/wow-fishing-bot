from __future__ import annotations

from wowfish.errors import NotSupported
from wowfish.input import MouseButton


class StubInputDevice:
    def press_key(self, key: str) -> None:
        raise NotSupported("input injection")

    def move_to(self, x: int, y: int, duration_s: float) -> None:
        raise NotSupported("input injection")

    def click(self, button: MouseButton) -> None:
        raise NotSupported("input injection")
