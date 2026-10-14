"""The fishing loop. One `step()` per iteration; every collaborator is injectable."""

from __future__ import annotations

import math
import queue
import random
import time
from collections.abc import Callable
from typing import Any

import cv2
import numpy as np

from wowfish.audio import AudioChunk
from wowfish.audio._threaded import ThreadedSource
from wowfish.capture import Box, WindowRef, find_window, get_capturer, linux_x11
from wowfish.config import Config
from wowfish.engine import events as ev
from wowfish.engine.state import State
from wowfish.vision.region import Region
from wowfish.vision.search import IconSearch

UNFOCUSED = "World of Warcraft is not the focused window; click into the game"
THUMB_WIDTH = 480
AUDIO_BLOCK = 1024
AUDIO_MAX_S = 2.0  # never read more than this at once; the device buffer may drop older audio
STATS_EVERY_S = 10.0
SLEEP_SLICE_S = 0.1


class FishingEngine:
    def __init__(
        self,
        cfg: Config,
        window: WindowRef,
        *,
        capturer: Any,
        input_device: Any,
        audio_source: Any,
        detector: Any,
        matcher: Any,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
        session_s: float | None = None,
        box_interval_s: float = 0.25,
        lost_after: int = 3,
    ) -> None:
        self.cfg = cfg
        self.window = window
        self.capturer = capturer
        self.input = input_device
        self.audio = audio_source
        self.detector = detector
        self.matcher = matcher
        self.search = IconSearch(matcher, cfg.vision.icon_threshold)
        self._clock = clock
        self._sleep = sleep
        self._rng = rng or random.Random()
        self.session_s = cfg.game.session_minutes * 60.0 if session_s is None else session_s
        self.box_interval_s = box_interval_s
        self.lost_after = lost_after

        self.events: queue.Queue[ev.Event] = queue.Queue()
        self.state = State.IDLE
        self.stats = ev.Stats(0.0)
        self.started: float | None = None
        self._stop = False
        self._resume_state = State.IDLE
        self._t_cast = 0.0
        self._t_interact = 0.0
        self._icon_xy: tuple[int, int] | None = None
        self._icon_size = 0
        self._misses = 0
        self._last_box_grab = -math.inf
        self._last_audio: float | None = None
        self._audio_frames = 0
        self._last_stats = 0.0

    # -- public ------------------------------------------------------------------------------

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        self.capturer.open(self.window)
        try:
            with self.audio:
                while self.state is not State.STOPPED:
                    self.step()
        finally:
            self.capturer.close()

    def step(self) -> None:
        if self.state is State.STOPPED:
            return
        now = self._clock()
        if self.started is None:
            self.started = now
            self._last_audio = now
        if self._stop:
            self._finish("user")
            return
        if now - self.started >= self.session_s:
            self._finish("session limit")
            return
        try:
            self._step(now)
        except Exception as e:  # a collaborator broke; say so and stop rather than spin
            self._emit(ev.Error(self._t(), f"{type(e).__name__}: {e}"))
            self._finish("error")

    # -- the loop body -----------------------------------------------------------------------

    def _step(self, now: float) -> None:
        focused = self.input.is_game_focused(self.window)
        if focused is False:
            if self.state is not State.PAUSED:
                self._resume_state = self.state
                self.state = State.PAUSED
                self._emit(ev.Paused(self._t(), UNFOCUSED))
            self._drain_audio(now)
            self._sleep(SLEEP_SLICE_S)
            return
        if self.state is State.PAUSED:
            self.state = self._resume_state
            self._emit(ev.Resumed(self._t(), self.state))

        chunks = self._drain_audio(now)
        bites = []
        if self.state is State.WAIT_BITE:
            for chunk in chunks:
                bites.extend(self.detector.feed(chunk))

        if self.state is State.IDLE:
            self._cast(now)
        elif self.state is State.CASTING:
            self._acquire(now)
        elif self.state is State.WAIT_BITE:
            self._wait_bite(now, bites)
        elif self.state is State.INTERACT:
            self._after_interact(now)
        self._maybe_stats(now)

    def _cast(self, now: float) -> None:
        key = self.cfg.game.cast_key
        self._press(key, "cast")
        self.stats = ev.Stats(
            self._t(), self.stats.casts + 1, self.stats.catches, self.stats.misses,
            self.stats.bites_heard, self._elapsed(),
        )  # fmt: skip
        self._t_cast = now
        self.search.reset()
        limit = self.cfg.run.icon_timeout_s
        self._change(
            State.CASTING,
            f"Pressed {key} to cast",
            f"Looking for the gear icon over the bobber for up to {limit:g} s",
        )

    def _acquire(self, now: float) -> None:
        frame = self.capturer.grab()
        _, m = self.search.step(frame)
        if m.accepted(self.cfg.vision.icon_threshold):
            self._found(frame, m)
            return
        if now - self._t_cast > self.cfg.run.icon_timeout_s:
            self._emit(ev.Timeout(self._t(), "icon", self.cfg.run.icon_timeout_s))
            self._miss("No gear icon over the bobber")

    def _found(self, frame: np.ndarray, m: Any) -> None:
        self._icon_xy = (m.x, m.y)
        self._icon_size = m.size
        self._misses = 0
        self._last_box_grab = self._clock()  # the full frame just confirmed it; look again later
        thumb, box = _thumbnail(frame, m.x, m.y, m.size)
        self._emit(ev.IconFound(self._t(), thumb, box, float(m.score), int(m.size), (m.x, m.y)))
        self.detector.reset()
        self._change(
            State.WAIT_BITE,
            f"Found the bobber at ({m.x}, {m.y})",
            f"Waiting for a splash; will press {self.cfg.game.interact_key} when I hear one",
        )

    def _wait_bite(self, now: float, bites: list[Any]) -> None:
        if bites:
            bite = bites[0]
            self.stats = ev.Stats(
                self._t(), self.stats.casts, self.stats.catches, self.stats.misses,
                self.stats.bites_heard + 1, self._elapsed(),
            )  # fmt: skip
            self._emit(ev.BiteHeard(self._t(), bite.clip, float(bite.score)))
            if self.input.is_game_focused(self.window) is False:
                self._resume_state = State.WAIT_BITE
                self.state = State.PAUSED
                self._emit(ev.Paused(self._t(), UNFOCUSED))
                return
            key = self.cfg.game.interact_key
            self._press(key, "bite")
            self._t_interact = now
            self._last_box_grab = -math.inf
            self._change(
                State.INTERACT,
                f"Heard the splash ({bite.score:.2f}), pressed {key}",
                "Waiting for the bobber to go away so Auto Loot can finish",
            )
            return
        seen = self._track(now)
        if seen is False and self._misses >= self.lost_after:
            self._emit(ev.IconLost(self._t()))
            self._miss("Lost sight of the bobber")
            return
        if now - self._t_cast > self.cfg.run.cast_timeout_s:
            self._emit(ev.Timeout(self._t(), "bite", self.cfg.run.cast_timeout_s))
            self._miss("No splash heard")

    def _after_interact(self, now: float) -> None:
        seen = self._track(now)
        if seen is False:
            self.stats = ev.Stats(
                self._t(), self.stats.casts, self.stats.catches + 1, self.stats.misses,
                self.stats.bites_heard, self._elapsed(),
            )  # fmt: skip
            self._emit(ev.Caught(self._t()))
            self._pause_then_idle("Caught something; the bobber is gone")
            return
        if now - self._t_interact > self.cfg.run.loot_timeout_s:
            self._emit(ev.Timeout(self._t(), "loot", self.cfg.run.loot_timeout_s))
            self._miss("The bobber did not go away after Interact")

    # -- helpers -----------------------------------------------------------------------------

    def _track(self, now: float) -> bool | None:
        """Grab the box around the icon (at most every box_interval_s) and look for it there.

        True = seen, False = not seen (misses counted), None = not time to look yet.
        """
        if now - self._last_box_grab < self.box_interval_s or self._icon_xy is None:
            return None
        self._last_box_grab = now
        x, y = self._icon_xy
        w, h = self.window.width, self.window.height
        x0, y0, x1, y1 = Region.around(x, y, w, h, 0.10).to_box(w, h)
        box: Box = (x0, y0, x1 - x0, y1 - y0)
        crop = self.capturer.grab(box)
        m = self.matcher.match(crop, full_width=w)
        if m.accepted(self.cfg.vision.icon_threshold):
            self._icon_xy = (x0 + m.x, y0 + m.y)
            self._misses = 0
            return True
        self._misses += 1
        return False

    def _press(self, key: str, why: str) -> None:
        self.input.press_key(key, self.cfg.run.key_hold_ms / 1000.0)
        self._emit(ev.KeyPressed(self._t(), key, why))

    def _miss(self, did: str) -> None:
        self.stats = ev.Stats(
            self._t(), self.stats.casts, self.stats.catches, self.stats.misses + 1,
            self.stats.bites_heard, self._elapsed(),
        )  # fmt: skip
        self._pause_then_idle(did)

    def _pause_then_idle(self, did: str) -> None:
        pause = self._rng.uniform(self.cfg.run.pause_min_s, self.cfg.run.pause_max_s)
        self._change(State.IDLE, did, f"Casting again in {pause:.1f} s")
        self._icon_xy = None
        remaining = pause
        while remaining > 0 and not self._stop:
            step = min(SLEEP_SLICE_S, remaining)
            self._sleep(step)
            remaining -= step

    def _drain_audio(self, now: float) -> list[AudioChunk]:
        rate = self.audio.sample_rate
        last = self._last_audio if self._last_audio is not None else now
        n = int((now - last) * rate)
        n = max(AUDIO_BLOCK, min(n, int(AUDIO_MAX_S * rate)))
        self._last_audio = now
        samples = self.audio.read(n)
        self._audio_frames += len(samples)
        return [AudioChunk(samples, rate, self._audio_frames / rate)]

    def _change(self, state: State, did: str, nxt: str) -> None:
        self.state = state
        self._emit(ev.StateChanged(self._t(), state, did, nxt))
        self._emit_stats()

    def _maybe_stats(self, now: float) -> None:
        if self.state is State.WAIT_BITE and now - self._last_stats >= STATS_EVERY_S:
            self._emit_stats()

    def _emit_stats(self) -> None:
        self._last_stats = self._clock()
        self.stats = ev.Stats(
            self._t(), self.stats.casts, self.stats.catches, self.stats.misses,
            self.stats.bites_heard, self._elapsed(),
        )  # fmt: skip
        self._emit(self.stats)

    def _finish(self, reason: str) -> None:
        if self.state is State.STOPPED:
            return
        self._emit_stats()
        self.state = State.STOPPED
        self._emit(ev.Stopped(self._t(), reason))

    def _emit(self, event: ev.Event) -> None:
        self.events.put(event)

    def _elapsed(self) -> float:
        return 0.0 if self.started is None else self._clock() - self.started

    def _t(self) -> float:
        return self._elapsed()


def _thumbnail(frame: np.ndarray, x: int, y: int, size: int) -> tuple[np.ndarray, Box]:
    h, w = frame.shape[:2]
    scale = min(1.0, THUMB_WIDTH / w)
    if scale < 1.0:
        thumb = cv2.resize(
            frame, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA
        )
    else:
        thumb = frame.copy()
    side = max(2, round(size * scale))
    bx = max(0, round(x * scale - side / 2))
    by = max(0, round(y * scale - side / 2))
    return thumb, (bx, by, side, side)


def unsupported_platform() -> str:
    """Why the bot cannot run here, or "" when it can (X11/Xwayland on Linux, or Windows)."""
    import os
    import sys

    if sys.platform == "win32" or linux_x11():
        return ""
    if sys.platform == "linux" and not os.environ.get("DISPLAY"):
        return "DISPLAY is not set; the bot needs X11 or Xwayland (log into a session with one)"
    return "the bot is not supported yet on this platform (Linux X11/Xwayland and Windows only)"


CALIBRATE_HINT = (
    "run `wowfish calibrate --save` on a screenshot with the gear icon visible, or use the GUI's "
    "Setup page"
)


def build_engine(
    cfg: Config, *, session_s: float | None = None, title: str = "World of Warcraft"
) -> FishingEngine:
    """Wire the real capturer, input device, audio source, detector, and matcher for `cfg`.

    Raises RuntimeError with a one-line hint when a prerequisite is missing.
    """
    from wowfish.assets import CLIP_FAMILIES
    from wowfish.audio.clips import build_fingerprints
    from wowfish.audio.detector import BiteDetector
    from wowfish.audio.devices import open_loopback
    from wowfish.input import get_input_device
    from wowfish.vision.matcher import MIN_TEMPLATE_PX, IconMatcher
    from wowfish.vision.template import load_icon_templates, template_for_size

    platform_problem = unsupported_platform()
    if platform_problem:
        raise RuntimeError(platform_problem)
    window = find_window(title)
    if window is None:
        raise RuntimeError(f"no window titled {title!r}; is the game running?")
    size = cfg.vision.icon_size_px
    if size <= 0:
        raise RuntimeError(f"the interact icon is not calibrated; {CALIBRATE_HINT}")
    matcher = IconMatcher(template_for_size(load_icon_templates(), size), cfg.vision.match_width)
    px = matcher.template_px(window.width)
    if px < MIN_TEMPLATE_PX:
        raise RuntimeError(
            f"icon_size_px={size} is {px} px after downscaling this {window.width}-wide window "
            f"(minimum {MIN_TEMPLATE_PX}); {CALIBRATE_HINT}"
        )
    detector = BiteDetector(
        build_fingerprints(),
        trigger_clips=CLIP_FAMILIES[cfg.audio.bite_clip],
        threshold=cfg.audio.bite_threshold,
        refractory_s=cfg.audio.refractory_s,
    )
    return FishingEngine(
        cfg,
        window,
        capturer=get_capturer(),
        input_device=get_input_device(),
        audio_source=ThreadedSource(open_loopback(cfg.audio.device)),
        detector=detector,
        matcher=matcher,
        session_s=session_s,
    )
