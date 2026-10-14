import numpy as np
import pytest

from wowfish import capture
from wowfish import input as wf_input
from wowfish.errors import NotSupported


class FakeCapturer:
    def open(self, window: capture.WindowRef) -> None:
        self.window = window

    def grab(self, box=None) -> np.ndarray:
        return np.zeros((2, 2, 3), dtype=np.uint8)

    def close(self) -> None:
        pass


class FakeInput:
    def press_key(self, key: str, hold_s: float = 0.06) -> None:
        pass

    def is_game_focused(self, window: capture.WindowRef) -> bool | None:
        return True


def test_fakes_satisfy_the_protocols():
    cap: capture.Capturer = FakeCapturer()
    dev: wf_input.InputDevice = FakeInput()
    assert isinstance(cap, capture.Capturer)
    assert isinstance(dev, wf_input.InputDevice)


def test_window_ref_is_a_plain_frozen_record():
    w = capture.WindowRef(
        title="World of Warcraft", pid=123, left=0, top=0, width=1920, height=1080
    )
    with pytest.raises(AttributeError):
        w.title = "x"  # type: ignore[misc]


def test_window_ref_handle_defaults_to_none():
    w = capture.WindowRef("t", None, 0, 0, 1, 1)
    assert w.handle is None


def test_stub_capturer_when_no_backend_is_available(monkeypatch):
    import sys

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.setitem(sys.modules, "mss", None)
    cap = capture.get_capturer()
    with pytest.raises(NotSupported) as exc:
        cap.open(capture.WindowRef("t", None, 0, 0, 1, 1))
    assert str(exc.value) == "wowfish does not support screen capture yet."


def test_find_window_is_none_where_discovery_is_not_implemented(monkeypatch):
    import sys

    monkeypatch.setattr(sys, "platform", "win32")
    assert capture.find_window("World of Warcraft") is None


def test_input_device_is_the_stub_and_says_so_without_a_display(monkeypatch):
    import sys

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    dev = wf_input.get_input_device()
    with pytest.raises(NotSupported) as exc:
        dev.press_key("1")
    assert str(exc.value) == "wowfish does not support input injection on this platform yet."
