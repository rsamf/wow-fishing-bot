import time

import cv2
import numpy as np
import pytest

from tests.fakes import (
    WINDOW,
    FakeAudio,
    FakeCapturer,
    FakeDetector,
    FakeInput,
    FakeMatcher,
    no_match,
)
from wowfish import paths
from wowfish.audio._file import WavFileSource
from wowfish.audio.devices import LoopbackDevice
from wowfish.config import AudioConfig, Config, GameConfig, VisionConfig, load_config
from wowfish.engine.engine import FishingEngine
from wowfish.gui import image
from wowfish.gui.presenter import CalibrateDone, Presenter, VerifyDone

ICON_FRAME = cv2.imread("tests/fixtures/wow_icon_crop.png")  # 1024x640, icon at (512, 320), 56 px
DEVICES = [
    LoopbackDevice("mon.a", "Monitor of A", False),
    LoopbackDevice("mon.b", "Monitor of B", True),
]


def _engine(cfg, session_s=None, title="World of Warcraft"):
    cfg = Config(
        game=GameConfig(cast_key="8"), vision=VisionConfig(icon_size_px=40), audio=AudioConfig()
    )
    return FishingEngine(
        cfg, WINDOW, capturer=FakeCapturer(), input_device=FakeInput(), audio_source=FakeAudio(),
        detector=FakeDetector(), matcher=FakeMatcher([no_match()]), session_s=0.3,
    )  # fmt: skip


def make(**kw):
    deps = {
        "build_engine": _engine,
        "list_devices": lambda: list(DEVICES),
        "open_loopback": lambda selector="": WavFileSource("tests/fixtures/bite_strong.wav"),
        "find_window": lambda title="World of Warcraft": WINDOW,
        "get_capturer": lambda: FakeCapturer(lambda i, box: ICON_FRAME.copy()),
    }
    deps.update(kw)
    return Presenter(**deps)


def wait_for(pres, kind, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for item in pres.poll().log_events:
            if isinstance(item, kind):
                return item
        time.sleep(0.02)
    raise AssertionError(f"no {kind.__name__} within {timeout}s")


def test_png_round_trip_and_box_drawing():
    frame = np.zeros((60, 80, 3), dtype=np.uint8)
    png = image.bgr_to_png_bytes(image.with_box(frame, (10, 10, 20, 20)))
    back = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
    assert back.shape == (60, 80, 3) and back[8, 8].tolist() != [0, 0, 0]  # the box edge
    assert image.png_base64(png).startswith("iVBOR")


def test_save_keys_validates_and_persists():
    pres = make()
    pres.save_keys("8", "F")
    cfg, _ = load_config()
    assert cfg.game.cast_key == "8" and cfg.game.interact_key == "f"
    with pytest.raises(ValueError):
        pres.save_keys("shift+8", "f")


def test_audio_devices_and_saving_the_choice():
    pres = make()
    names = [d.name for d in pres.audio_devices()]
    assert names == ["Monitor of A", "Monitor of B"]
    assert pres.default_device().id == "mon.b"
    pres.save_audio_device("mon.a")
    assert load_config()[0].audio.device == "mon.a"


def test_prerequisites_name_what_blocks_start():
    pres = make(find_window=lambda title="World of Warcraft": None)
    reasons = pres.prerequisites()
    assert any("World of Warcraft" in r for r in reasons)
    assert not any("calibrat" in r for r in reasons)  # the first cast measures the icon
    pres = make()
    assert pres.prerequisites() == []


def test_grab_and_calibrate_posts_a_result_and_save_persists():
    pres = make()
    pres.grab_and_calibrate()
    done = wait_for(pres, CalibrateDone)
    assert done.calibration.valid and 50 <= done.calibration.icon_size_px <= 62
    assert done.thumbnail_png[:4] == b"\x89PNG"
    pres.save_calibration()
    cfg, _ = load_config()
    assert cfg.vision.icon_size_px == done.calibration.icon_size_px
    assert cfg.vision.icon_threshold == done.calibration.suggested_threshold()


def test_record_and_verify_posts_a_report():
    pres = make()
    pres.record_and_verify(seconds=3.0)
    done = wait_for(pres, VerifyDone, timeout=20.0)
    assert done.report.stands_out and len(done.report.bites) == 1
    assert done.recording.exists()
    pres.save_bite_threshold()
    assert load_config()[0].audio.bite_threshold == done.report.threshold


def test_meter_reports_level_then_stops():
    pres = make()
    pres.start_meter()
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline and pres.level_dbfs <= -100:
        time.sleep(0.02)
    assert pres.level_dbfs > -60
    pres.stop_meter()
    assert not pres.meter_running


def test_start_runs_the_engine_and_poll_builds_the_view():
    paths.config_file().write_text("[vision]\nicon_size_px = 56\n")
    pres = make()
    pres.start()
    deadline = time.monotonic() + 5.0
    log: list[str] = []
    view = None
    while time.monotonic() < deadline:
        view = pres.poll()
        log += view.new_lines
        if view.state == "STOPPED":
            break
        time.sleep(0.02)
    assert view is not None and view.state == "STOPPED"
    assert any("Pressed 8 to cast" in line for line in log)
    assert any("Stopped (session limit)" in line for line in log)
    assert view.stats.startswith("casts 1,")
    assert view.did == "Stopped (session limit)"
    assert not pres.running


def test_shutdown_stops_a_running_engine():
    def forever(cfg, session_s=None, title="World of Warcraft"):
        e = _engine(cfg)
        e.session_s = 3600.0
        return e

    paths.config_file().write_text("[vision]\nicon_size_px = 56\n")
    pres = make(build_engine=forever)
    pres.start()
    time.sleep(0.1)
    assert pres.running
    t0 = time.monotonic()
    pres.shutdown()
    assert time.monotonic() - t0 < 3.0 and not pres.running


def test_start_failure_is_reported_not_raised():
    def boom(cfg, session_s=None, title="World of Warcraft"):
        raise RuntimeError("no window titled 'World of Warcraft'; is the game running?")

    paths.config_file().write_text("[vision]\nicon_size_px = 56\n")
    pres = make(build_engine=boom)
    pres.start()
    view = pres.poll()
    assert any("is the game running" in line for line in view.new_lines)
    assert not pres.running


def test_resumed_restores_the_state_badge():
    from wowfish.engine import events as ev
    from wowfish.engine.state import State

    pres = make()
    pres._apply(ev.StateChanged(1.0, State.WAIT_BITE, "Found the bobber at (1, 2)", "Waiting"))
    pres._apply(ev.Paused(2.0, "World of Warcraft is not the focused window"))
    assert pres.state == "PAUSED"
    pres._apply(ev.Resumed(3.0, State.WAIT_BITE))
    assert pres.state == "WAIT_BITE" and pres.did == "Found the bobber at (1, 2)"


def test_prerequisites_say_not_supported_off_x11_and_windows(monkeypatch):
    import sys

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.delenv("DISPLAY", raising=False)
    pres = make(find_window=lambda title="World of Warcraft": None)
    assert any("not supported yet" in r for r in pres.prerequisites())
