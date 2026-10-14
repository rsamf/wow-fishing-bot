import os
import sys
import time

import numpy as np
import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "linux" or not os.environ.get("DISPLAY"), reason="needs an X display"
)
pytest.importorskip("Xlib")


@pytest.fixture
def mapped_window():
    """A small top-level X window of our own, mapped and viewable."""
    from Xlib import X, display

    d = display.Display()
    screen = d.screen()
    win = screen.root.create_window(
        10, 10, 40, 30, 0, screen.root_depth, X.InputOutput, X.CopyFromParent,
        background_pixel=0x2040C0, event_mask=X.ExposureMask,
    )  # fmt: skip
    win.set_wm_name("wowfish test window")
    win.map()
    d.flush()
    deadline = time.time() + 3.0
    while time.time() - deadline < 0 and win.get_attributes().map_state != X.IsViewable:
        time.sleep(0.05)
    yield d, win
    win.destroy()
    d.flush()
    d.close()


def test_unknown_title_is_none():
    from wowfish.capture._x11 import find_window_x11

    assert find_window_x11("no window has this title 7f3a") is None


def test_find_and_grab_our_own_window(mapped_window):
    from Xlib import X

    from wowfish.capture._x11 import X11WindowCapturer, find_window_x11

    _d, win = mapped_window
    if win.get_attributes().map_state != X.IsViewable:
        pytest.skip("window manager did not map the test window in time")
    ref = find_window_x11("wowfish test window")
    assert ref is not None and ref.handle == win.id and (ref.width, ref.height) == (40, 30)
    origin = _d.screen().root.translate_coords(win, 0, 0)
    assert (ref.left, ref.top) == (origin.x, origin.y)
    cap = X11WindowCapturer()
    cap.open(ref)
    try:
        frame = cap.grab((0, 0, 4, 3))
    finally:
        cap.close()
    assert frame.shape == (3, 4, 3) and frame.dtype == np.uint8


def test_bad_handle_raises_instead_of_killing_the_process():
    from wowfish.capture import WindowRef
    from wowfish.capture._x11 import X11WindowCapturer

    cap = X11WindowCapturer()
    cap.open(WindowRef("ghost", None, 0, 0, 8, 8, handle=0x7FFFFFFF))
    try:
        with pytest.raises(RuntimeError):
            cap.grab((0, 0, 2, 2))
    finally:
        cap.close()
