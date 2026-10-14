import os
import sys
import weakref

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform == "linux" and not os.environ.get("DISPLAY"), reason="needs a display"
)


def test_window_builds_polls_and_closes(monkeypatch):
    pytest.importorskip("ttkbootstrap")
    import tkinter

    from tests.test_gui_presenter import make
    from wowfish.gui.app import App

    pres = make()
    try:
        app = App(pres)
    except tkinter.TclError as e:  # no usable display
        pytest.skip(f"Tk cannot open a window here: {e}")
    app.root.update()
    app.tick()
    assert app.root.winfo_exists()
    root_ref = weakref.ref(app.root)
    app.close()
    assert not pres.running
    # The Tk interpreter must be freed here, on the thread that made it: Tcl panics (SIGILL)
    # when a later garbage collection on another thread deletes it instead.
    assert app.root is None and root_ref() is None
