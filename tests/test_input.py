import os
import sys

import pytest

from wowfish import input as wf_input
from wowfish.capture import WindowRef
from wowfish.errors import InputUnavailable
from wowfish.input import keys

WINDOW = WindowRef("World of Warcraft", None, 0, 0, 100, 100, handle=1)


def test_normalize_key_lowercases_and_strips():
    assert keys.normalize_key("F") == "f"
    assert keys.normalize_key(" F5 ") == "f5"
    assert keys.normalize_key("Space") == "space"


@pytest.mark.parametrize("name", ["f", "8", "f12", "space", "enter", "-", "`", "\\"])
def test_supported_keys(name):
    assert keys.is_supported_key(name)


@pytest.mark.parametrize("name", ["shift+8", "", "ctrl", "f13", "ab"])
def test_unsupported_keys(name):
    assert not keys.is_supported_key(name)


def test_x11_name_table_covers_every_supported_key():
    assert set(keys.X11_NAMES) == set(keys.SUPPORTED_KEYS)
    assert keys.X11_NAMES["f5"] == "F5" and keys.X11_NAMES["enter"] == "Return"


def test_vk_table_covers_every_supported_key():
    assert set(keys.VK_CODES) == set(keys.SUPPORTED_KEYS)
    assert keys.VK_CODES["a"] == 0x41 and keys.VK_CODES["f1"] == 0x70 and keys.VK_CODES["8"] == 0x38


def test_stub_device_without_a_display(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    dev = wf_input.get_input_device()
    assert isinstance(dev, wf_input.InputDevice)
    with pytest.raises(InputUnavailable):
        dev.press_key("f")
    assert dev.is_game_focused(WINDOW) is None


@pytest.mark.skipif(
    sys.platform != "linux" or not os.environ.get("DISPLAY"), reason="needs an X display"
)
def test_x11_device_contract_without_pressing_anything():
    from wowfish.input._x11 import X11InputDevice, xtest_available

    ok, detail = xtest_available()
    assert isinstance(ok, bool) and isinstance(detail, str)
    dev = X11InputDevice()
    assert isinstance(dev, wf_input.InputDevice)
    assert dev.is_game_focused(WindowRef("nope", None, 0, 0, 1, 1, handle=1)) is False
    dev.close()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_win32_device_contract_without_pressing_anything():
    from wowfish.input._win32 import Win32InputDevice

    dev = Win32InputDevice()
    assert isinstance(dev, wf_input.InputDevice)
    assert dev.is_game_focused(WindowRef("nope", None, 0, 0, 1, 1, handle=1)) is False
