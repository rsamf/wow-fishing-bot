import random

import numpy as np
import pytest

from tests.fakes import (
    WINDOW,
    FakeAudio,
    FakeCapturer,
    FakeClock,
    FakeDetector,
    FakeInput,
    FakeMatcher,
    blank,
    match,
    no_match,
)
from wowfish.audio.detector import BiteEvent
from wowfish.capture import WindowRef
from wowfish.config import AudioConfig, Config, GameConfig, RunConfig, VisionConfig
from wowfish.engine import events as ev
from wowfish.engine.engine import FishingEngine
from wowfish.engine.state import State

CFG = Config(
    game=GameConfig(cast_key="8", interact_key="f", session_minutes=60),
    vision=VisionConfig(icon_size_px=40, icon_threshold=0.75),
    audio=AudioConfig(),
    run=RunConfig(pause_min_s=0.5, pause_max_s=0.5, key_hold_ms=50),
)


def make(**kw):
    deps = {
        "capturer": FakeCapturer(),
        "input_device": FakeInput(),
        "audio_source": FakeAudio(),
        "detector": FakeDetector(),
        "matcher": FakeMatcher(),
        "clock": FakeClock(),
    }
    deps.update(kw)
    clock = deps["clock"]
    eng = FishingEngine(
        kw.get("cfg", CFG),
        WINDOW,
        capturer=deps["capturer"],
        input_device=deps["input_device"],
        audio_source=deps["audio_source"],
        detector=deps["detector"],
        matcher=deps["matcher"],
        clock=clock,
        sleep=clock.sleep,
        rng=random.Random(0),
    )
    return eng, deps


def drain(eng):
    out = []
    while not eng.events.empty():
        out.append(eng.events.get_nowait())
    return out


def kinds(events):
    return [type(e).__name__ for e in events]


def test_idle_casts_and_enters_casting():
    eng, d = make()
    eng.step()
    assert eng.state is State.CASTING
    assert d["input_device"].presses == [("8", 0.05)]
    evs = drain(eng)
    assert kinds(evs)[:2] == ["KeyPressed", "StateChanged"]
    sc = evs[1]
    assert sc.state is State.CASTING and sc.did == "Pressed 8 to cast"
    assert sc.next == "Looking for the gear icon over the bobber for up to 6 s"
    assert eng.stats.casts == 1


def test_icon_found_enters_wait_bite_resets_detector_and_emits_thumbnail():
    frame = blank()
    frame[140:160, 190:210] = 255
    eng, d = make(capturer=FakeCapturer(lambda i, box: frame.copy()))
    eng.step()  # cast
    eng.step()  # acquire on the full frame
    assert eng.state is State.WAIT_BITE
    assert d["detector"].resets == 1
    assert d["capturer"].grabs == [None]  # the acquire grab is the full window
    evs = drain(eng)
    found = next(e for e in evs if isinstance(e, ev.IconFound))
    assert found.thumbnail.shape[1] <= 480 and found.where == (200, 150) and found.size == 40
    x, _y, w, h = found.box
    assert 0 <= x < found.thumbnail.shape[1] and w > 0 and h > 0
    sc = [e for e in evs if isinstance(e, ev.StateChanged)][-1]
    assert sc.did == "Found the bobber at (200, 150)"
    assert sc.next == "Waiting for a splash; will press f when I hear one"


def test_icon_timeout_recasts_and_counts_a_miss():
    clock = FakeClock()
    eng, _d = make(matcher=FakeMatcher([no_match()]), clock=clock)
    eng.step()  # cast at t0
    clock.t += 6.5
    eng.step()  # acquire fails past icon_timeout_s
    evs = drain(eng)
    assert any(isinstance(e, ev.Timeout) and e.what == "icon" and e.after_s == 6.0 for e in evs)
    assert eng.stats.misses == 1 and eng.state is State.IDLE
    assert clock.sleeps and abs(sum(clock.sleeps) - 0.5) < 1e-6  # the random pause (min == max)
    sc = [e for e in evs if isinstance(e, ev.StateChanged)][-1]
    assert sc.state is State.IDLE and sc.next == "Casting again in 0.5 s"
    eng.step()
    assert eng.stats.casts == 2 and eng.state is State.CASTING


def _to_wait_bite(**kw):
    eng, d = make(**kw)
    eng.step()
    eng.step()
    assert eng.state is State.WAIT_BITE
    drain(eng)
    return eng, d


def test_bite_presses_interact_and_enters_interact():
    det = FakeDetector({1: [BiteEvent("fishingbobber_2", 0.84, 12.0)]})
    eng, d = _to_wait_bite(detector=det)
    eng.step()
    assert eng.state is State.INTERACT
    assert d["input_device"].presses[-1] == ("f", 0.05)
    evs = drain(eng)
    assert kinds(evs)[:3] == ["BiteHeard", "KeyPressed", "StateChanged"]
    assert evs[0].score == 0.84 and evs[1].why == "bite"
    assert evs[2].did == "Heard the splash (0.84), pressed f"
    assert evs[2].next == "Waiting for the bobber to go away so Auto Loot can finish"
    assert eng.stats.bites_heard == 1


def test_icon_gone_after_interact_counts_a_catch():
    det = FakeDetector({1: [BiteEvent("fishingbobber_2", 0.84, 12.0)]})
    clock = FakeClock()
    # acquire: found; first tracking crop after Interact: gone
    m = FakeMatcher([match(), no_match()])
    eng, _d = _to_wait_bite(detector=det, matcher=m, clock=clock)
    eng.step()  # bite -> interact
    clock.t += 0.3
    eng.step()  # tracking crop says gone
    evs = drain(eng)
    assert any(isinstance(e, ev.Caught) for e in evs)
    assert eng.stats.catches == 1 and eng.state is State.IDLE


def test_loot_timeout_counts_a_miss():
    det = FakeDetector({1: [BiteEvent("fishingbobber_2", 0.84, 12.0)]})
    clock = FakeClock()
    eng, _d = _to_wait_bite(detector=det, clock=clock)
    eng.step()  # interact
    clock.t += 3.5
    eng.step()
    evs = drain(eng)
    assert any(isinstance(e, ev.Timeout) and e.what == "loot" for e in evs)
    assert eng.stats.misses == 1 and eng.stats.catches == 0 and eng.state is State.IDLE


def test_bite_timeout_counts_a_miss():
    clock = FakeClock()
    eng, _d = _to_wait_bite(clock=clock)
    clock.t += 31.0
    eng.step()
    evs = drain(eng)
    assert any(isinstance(e, ev.Timeout) and e.what == "bite" and e.after_s == 30.0 for e in evs)
    assert eng.stats.misses == 1 and eng.state is State.IDLE


def test_icon_lost_needs_three_consecutive_misses():
    clock = FakeClock()
    m = FakeMatcher([match(), no_match(), match(), no_match(), no_match(), no_match()])
    eng, _d = _to_wait_bite(matcher=m, clock=clock)
    for _ in range(3):  # miss, hit, miss: not lost
        clock.t += 0.3
        eng.step()
    assert eng.state is State.WAIT_BITE
    for _ in range(2):
        clock.t += 0.3
        eng.step()
    evs = drain(eng)
    assert any(isinstance(e, ev.IconLost) for e in evs)
    assert eng.state is State.IDLE and eng.stats.misses == 1


def test_box_grab_used_while_tracking():
    clock = FakeClock()
    eng, d = _to_wait_bite(clock=clock)
    clock.t += 0.3
    eng.step()
    box = d["capturer"].grabs[-1]
    assert box is not None
    x, y, w, h = box
    assert x < 200 < x + w and y < 150 < y + h and w < 400
    (shape, region, _kw) = d["matcher"].calls[-1]
    assert shape == (h, w) and region is None


def test_tracking_grabs_at_most_four_times_a_second():
    clock = FakeClock()
    eng, d = _to_wait_bite(clock=clock)
    n0 = len(d["capturer"].grabs)
    for _ in range(5):
        clock.t += 0.03
        eng.step()
    assert len(d["capturer"].grabs) == n0
    clock.t += 0.25
    eng.step()
    assert len(d["capturer"].grabs) == n0 + 1


def test_unfocused_pauses_and_never_presses():
    eng, d = make(input_device=FakeInput(False))
    eng.step()
    eng.step()
    assert eng.state is State.PAUSED and d["input_device"].presses == []
    evs = drain(eng)
    paused = [e for e in evs if isinstance(e, ev.Paused)]
    assert len(paused) == 1
    assert paused[0].reason == "World of Warcraft is not the focused window; click into the game"


def test_refocus_resumes_the_same_state():
    eng, _d = _to_wait_bite(input_device=FakeInput([True, True, False, True, True]))
    eng.step()
    assert eng.state is State.PAUSED
    eng.step()
    assert eng.state is State.WAIT_BITE
    evs = drain(eng)
    assert kinds(evs)[:2] == ["Paused", "Resumed"]


def test_focus_lost_mid_step_pauses_before_the_next_press():
    det = FakeDetector({1: [BiteEvent("fishingbobber_2", 0.84, 12.0)]})
    eng, d = _to_wait_bite(detector=det, input_device=FakeInput([True, True, False, False]))
    eng.step()  # focus gone right when the bite arrives: no interact press
    assert eng.state is State.PAUSED
    assert [k for k, _ in d["input_device"].presses] == ["8"]


def test_unknown_focus_counts_as_focused():
    eng, d = make(input_device=FakeInput(None))
    eng.step()
    assert eng.state is State.CASTING and d["input_device"].presses


def test_audio_is_drained_every_step_even_outside_wait_bite():
    clock = FakeClock()
    eng, d = make(matcher=FakeMatcher([no_match()]), clock=clock)
    eng.step()  # cast
    clock.t += 0.5
    eng.step()  # casting, no icon
    reads = d["audio_source"].reads
    assert len(reads) >= 2 and reads[-1] >= int(0.5 * 22050)
    assert d["detector"].feeds == 0


def test_detector_only_fed_in_wait_bite():
    clock = FakeClock()
    eng, d = _to_wait_bite(clock=clock)
    clock.t += 0.1
    eng.step()
    assert d["detector"].feeds == 1


def test_audio_read_is_capped_after_a_long_gap():
    clock = FakeClock()
    eng, d = make(clock=clock)
    clock.t += 60.0
    eng.step()
    assert max(d["audio_source"].reads) <= 2 * 22050


def test_stop_during_pause_returns_quickly():
    import threading
    import time

    clock = FakeClock()
    real_sleeps = []

    def slow_sleep(s):
        real_sleeps.append(s)
        time.sleep(s)
        clock.t += s

    cfg = Config(
        game=GameConfig(), vision=VisionConfig(icon_size_px=40), audio=AudioConfig(),
        run=RunConfig(pause_min_s=5.0, pause_max_s=5.0),
    )  # fmt: skip
    eng, _d = make(cfg=cfg, matcher=FakeMatcher([no_match()]), clock=clock)
    eng._sleep = slow_sleep
    eng.step()  # cast
    clock.t += 7.0
    threading.Timer(0.15, eng.stop).start()
    t0 = time.monotonic()
    eng.step()  # icon timeout -> 5 s pause, interrupted by stop
    eng.step()
    assert time.monotonic() - t0 < 1.0
    assert eng.state is State.STOPPED
    assert any(isinstance(e, ev.Stopped) and e.reason == "user" for e in drain(eng))


def test_session_limit_stops():
    clock = FakeClock()
    eng, _d = make(clock=clock)
    eng.step()
    clock.t += 60 * 60 + 1
    eng.step()
    evs = drain(eng)
    assert eng.state is State.STOPPED
    assert any(isinstance(e, ev.Stopped) and e.reason == "session limit" for e in evs)
    assert isinstance(evs[-2], ev.Stats)


def test_collaborator_error_emits_error_and_stops():
    class Boom(FakeCapturer):
        def grab(self, box=None):
            raise RuntimeError("X connection lost")

    eng, _d = make(capturer=Boom())
    eng.step()  # cast
    eng.step()  # grab raises
    evs = drain(eng)
    assert eng.state is State.STOPPED
    assert any(isinstance(e, ev.Error) and "X connection lost" in e.message for e in evs)
    assert evs[-1].reason == "error"


def test_stats_counts_and_periodic_emission():
    clock = FakeClock()
    eng, _d = _to_wait_bite(clock=clock)
    for _ in range(3):
        clock.t += 4.0
        eng.step()
    stats = [e for e in drain(eng) if isinstance(e, ev.Stats)]
    assert len(stats) == 1 and stats[0].casts == 1 and stats[0].elapsed_s >= 12.0


def test_run_opens_and_closes_collaborators_and_honours_stop():
    eng, d = make()
    eng.stop()
    eng.run()
    assert d["capturer"].opened == WINDOW and d["capturer"].closed
    assert d["audio_source"].entered == 1 and d["audio_source"].exited == 1
    assert eng.state is State.STOPPED


def test_thumbnail_box_marks_the_icon_on_a_big_frame():
    big = np.zeros((1080, 1920, 3), dtype=np.uint8)
    eng, _d = make(
        capturer=FakeCapturer(lambda i, box: big if box is None else blank(box[3], box[2])),
        matcher=FakeMatcher([match(0.9, 1500, 400, 56)]),
    )
    eng.step()
    eng.step()
    found = next(e for e in drain(eng) if isinstance(e, ev.IconFound))
    assert found.thumbnail.shape == (270, 480, 3)
    x, y, w, h = found.box
    assert abs((x + w / 2) - 1500 / 4) <= 2 and abs((y + h / 2) - 400 / 4) <= 2
    assert w == pytest.approx(56 / 4, abs=2)


def test_build_engine_refuses_without_calibration(monkeypatch):
    from wowfish.engine import engine as engine_mod

    monkeypatch.setattr(engine_mod, "find_window", lambda title="World of Warcraft": WINDOW)
    cfg = Config(game=GameConfig(), vision=VisionConfig(icon_size_px=0), audio=AudioConfig())
    with pytest.raises(RuntimeError) as exc:
        engine_mod.build_engine(cfg)
    assert "wowfish calibrate --save" in str(exc.value)


def test_build_engine_refuses_without_a_window(monkeypatch):
    from wowfish.engine import engine as engine_mod

    monkeypatch.setattr(engine_mod, "find_window", lambda title="World of Warcraft": None)
    cfg = Config(game=GameConfig(), vision=VisionConfig(icon_size_px=40), audio=AudioConfig())
    with pytest.raises(RuntimeError) as exc:
        engine_mod.build_engine(cfg)
    assert "is the game running" in str(exc.value)


def test_build_engine_refuses_an_icon_size_below_the_floor(monkeypatch):
    from wowfish.engine import engine as engine_mod

    big = WindowRef("World of Warcraft", None, 0, 0, 4986, 2816, handle=1)
    monkeypatch.setattr(engine_mod, "find_window", lambda title="World of Warcraft": big)
    cfg = Config(game=GameConfig(), vision=VisionConfig(icon_size_px=19), audio=AudioConfig())
    with pytest.raises(RuntimeError) as exc:
        engine_mod.build_engine(cfg)
    assert "7 px" in str(exc.value) and "calibrate" in str(exc.value)


def test_tracking_matches_the_crop_at_the_window_scale():
    big = WindowRef("World of Warcraft", None, 0, 0, 4986, 2816, handle=1)
    clock = FakeClock()
    eng, d = make(clock=clock)
    eng.window = big
    eng.step()
    eng.step()
    clock.t += 0.3
    eng.step()
    _shape, _region, kwargs = d["matcher"].calls[-1]
    assert kwargs.get("full_width") == 4986


def test_resumed_carries_the_state_it_returns_to():
    eng, _d = _to_wait_bite(input_device=FakeInput([True, True, False, True, True]))
    eng.step()
    eng.step()
    resumed = next(e for e in drain(eng) if isinstance(e, ev.Resumed))
    assert resumed.state is State.WAIT_BITE


def test_build_engine_says_not_supported_off_x11_and_windows(monkeypatch):
    import sys

    from wowfish.engine import engine as engine_mod

    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.delenv("DISPLAY", raising=False)
    cfg = Config(game=GameConfig(), vision=VisionConfig(icon_size_px=40), audio=AudioConfig())
    with pytest.raises(RuntimeError) as exc:
        engine_mod.build_engine(cfg)
    assert "not supported yet" in str(exc.value)
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(RuntimeError) as exc:
        engine_mod.build_engine(cfg)
    assert "DISPLAY" in str(exc.value)
