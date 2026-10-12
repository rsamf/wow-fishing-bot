"""Keyboard and mouse boundary. Real implementations arrive with the bot runtime."""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

MouseButton = Literal["left", "right"]


@runtime_checkable
class InputDevice(Protocol):
    def press_key(self, key: str) -> None: ...

    def move_to(self, x: int, y: int, duration_s: float) -> None: ...

    def click(self, button: MouseButton) -> None: ...


def get_input_device() -> InputDevice:
    from wowfish.input._stub import StubInputDevice

    return StubInputDevice()


__all__ = ["InputDevice", "MouseButton", "get_input_device"]
