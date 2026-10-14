"""XTest key presses through python-xlib, and a focus check against the game window."""

from __future__ import annotations

import os
import time
from typing import Any

from wowfish.capture import WindowRef
from wowfish.errors import InputUnavailable
from wowfish.input.keys import X11_NAMES, is_supported_key, normalize_key


def _open_display() -> Any:
    from Xlib import display

    try:
        return display.Display()
    except Exception as e:  # DisplayConnectionError and friends
        raise InputUnavailable(f"X11 input (cannot open display: {e})") from e


def xtest_available() -> tuple[bool, str]:
    """Whether the XTEST extension answers, and which server this is."""
    try:
        d = _open_display()
    except InputUnavailable as e:
        return False, str(e)
    try:
        ok = d.query_extension("XTEST") is not None
    finally:
        d.close()
    server = "Xwayland" if os.environ.get("WAYLAND_DISPLAY") else "X11"
    if not ok:
        return False, f"XTEST extension missing on {server}"
    note = (
        " (GNOME asks for Remote Desktop permission on the first key press; click Allow)"
        if server == "Xwayland"
        else ""
    )
    return True, f"XTest on {server}{note}"


class X11InputDevice:
    def __init__(self) -> None:
        self._d = _open_display()

    def close(self) -> None:
        if self._d is not None:
            self._d.close()
            self._d = None

    def press_key(self, key: str, hold_s: float = 0.06) -> None:
        from Xlib import XK, X
        from Xlib.ext import xtest

        name = normalize_key(key)
        if not is_supported_key(name):
            raise InputUnavailable(f"key {key!r} (not a supported key name)")
        keysym = XK.string_to_keysym(X11_NAMES[name])
        keycode = self._d.keysym_to_keycode(keysym)
        if not keycode:
            raise InputUnavailable(f"key {key!r} (no keycode on this keyboard layout)")
        xtest.fake_input(self._d, X.KeyPress, keycode)
        self._d.sync()
        time.sleep(hold_s)
        xtest.fake_input(self._d, X.KeyRelease, keycode)
        self._d.sync()

    def is_game_focused(self, window: WindowRef) -> bool | None:
        if window.handle is None:
            return None
        try:
            focus = self._d.get_input_focus().focus
        except Exception:
            return None
        if not hasattr(focus, "id"):
            return False  # PointerRoot / None: nothing focused
        w = focus
        for _ in range(64):
            if w.id == window.handle:
                return True
            try:
                parent = w.query_tree().parent
            except Exception:
                return False
            if not hasattr(parent, "id") or parent.id in (0, w.id):
                return False  # reached the root (python-xlib gives an int there)
            w = parent
        return False
