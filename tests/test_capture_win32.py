import sys

import numpy as np
import pytest

from wowfish import capture
from wowfish.capture import WindowRef, _mss
from wowfish.capture._win32 import client_rect_to_box


def test_client_rect_to_box_uses_the_client_origin_in_screen_pixels():
    # GetClientRect gives (0, 0, right, bottom); ClientToScreen gives where (0, 0) sits on screen.
    assert client_rect_to_box(0, 0, 1920, 1080, 100, 50) == (100, 50, 1920, 1080)
    assert client_rect_to_box(0, 0, 0, 0, 5, 5) == (5, 5, 0, 0)


def test_find_window_dispatches_to_win32(monkeypatch):
    from wowfish.capture import _win32

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("DISPLAY", raising=False)
    ref = WindowRef("World of Warcraft", None, 1, 2, 30, 40, handle=77)
    monkeypatch.setattr(_win32, "find_window_win32", lambda title: ref)
    assert capture.find_window("World of Warcraft") == ref


def test_find_window_is_none_on_macos(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.delenv("DISPLAY", raising=False)
    assert capture.find_window("World of Warcraft") is None


class _FakeShot:
    def __init__(self, area):
        self.area = area
        self.data = np.zeros((area["height"], area["width"], 4), dtype=np.uint8)
        self.data[:, :, 3] = 255

    def __array__(self, dtype=None, copy=None):
        return self.data


class _FakeMss:
    def __init__(self):
        self.areas = []

    def grab(self, area):
        self.areas.append(dict(area))
        return _FakeShot(area)

    def close(self):
        pass


def test_mss_grab_box_offsets_by_window_origin(monkeypatch):
    fake = _FakeMss()
    monkeypatch.setattr(_mss, "_mss_instance", lambda: fake)
    cap = _mss.MssCapturer()
    cap.open(WindowRef("w", None, 100, 50, 800, 600))
    full = cap.grab()
    crop = cap.grab((10, 20, 30, 40))
    cap.close()
    assert full.shape == (600, 800, 3) and crop.shape == (40, 30, 3)
    assert fake.areas[0] == {"left": 100, "top": 50, "width": 800, "height": 600}
    assert fake.areas[1] == {"left": 110, "top": 70, "width": 30, "height": 40}


def test_get_capturer_is_mss_off_x11(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("DISPLAY", raising=False)
    assert isinstance(capture.get_capturer(), _mss.MssCapturer)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_find_window_win32_returns_none_for_an_unknown_title():
    from wowfish.capture._win32 import find_window_win32

    assert find_window_win32("no such window title 0xdeadbeef") is None
