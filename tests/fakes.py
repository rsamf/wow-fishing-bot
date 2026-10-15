"""Scripted collaborators for engine tests. Nothing here touches a screen, a key, or a device."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from wowfish.audio.detector import BiteEvent, ClipScore
from wowfish.capture import Box, WindowRef
from wowfish.vision.matcher import NO_MATCH, IconMatch

WINDOW = WindowRef("World of Warcraft", None, 0, 0, 400, 300, handle=42)


def blank(h: int = 300, w: int = 400) -> np.ndarray:
    return np.zeros((h, w, 3), dtype=np.uint8)


class FakeCapturer:
    def __init__(self, frame_fn: Callable[[int, Box | None], np.ndarray] | None = None) -> None:
        self.frame_fn = frame_fn or (lambda i, box: blank(box[3], box[2]) if box else blank())
        self.grabs: list[Box | None] = []
        self.opened: WindowRef | None = None
        self.closed = False

    def open(self, window: WindowRef) -> None:
        self.opened = window

    def grab(self, box: Box | None = None) -> np.ndarray:
        self.grabs.append(box)
        return self.frame_fn(len(self.grabs) - 1, box)

    def close(self) -> None:
        self.closed = True


class FakeInput:
    def __init__(self, focused: bool | list[bool | None] | None = True) -> None:
        self._focused = list(focused) if isinstance(focused, list) else [focused]
        self.presses: list[tuple[str, float]] = []
        self.focus_checks = 0

    def is_game_focused(self, window: WindowRef) -> bool | None:
        self.focus_checks += 1
        if len(self._focused) > 1:
            return self._focused.pop(0)
        return self._focused[0]

    def press_key(self, key: str, hold_s: float = 0.06) -> None:
        self.presses.append((key, hold_s))


class FakeAudio:
    sample_rate = 22050

    def __init__(self) -> None:
        self.reads: list[int] = []
        self.entered = 0
        self.exited = 0

    def __enter__(self) -> FakeAudio:
        self.entered += 1
        return self

    def __exit__(self, *exc: object) -> None:
        self.exited += 1

    def read(self, n_frames: int) -> np.ndarray:
        self.reads.append(n_frames)
        return np.zeros(n_frames, dtype=np.float32)


class FakeDetector:
    def __init__(self, bites_at_feed: dict[int, list[BiteEvent]] | None = None) -> None:
        self.bites_at_feed = bites_at_feed or {}
        self.feeds = 0
        self.resets = 0
        self.level_dbfs = -30.0
        self.scores: dict[str, float] = {"fishingbobber_2": 0.41, "fishbite": 0.2}

    @property
    def last_scores(self) -> tuple[ClipScore, ...]:
        return tuple(ClipScore(n, s, 0.0) for n, s in self.scores.items())

    def reset(self) -> None:
        self.resets += 1

    def feed(self, chunk) -> list[BiteEvent]:
        self.feeds += 1
        return list(self.bites_at_feed.get(self.feeds, []))


def match(score: float = 0.9, x: int = 200, y: int = 150, size: int = 40) -> IconMatch:
    return IconMatch(score, x, y, size, 0.3)


def no_match(size: int = 40) -> IconMatch:
    return IconMatch(NO_MATCH, -1, -1, size, 0.0)


class FakeMatcher:
    """`script[i]` is the IconMatch returned by the i-th call; the last entry repeats."""

    def __init__(self, script: list[IconMatch] | None = None, size: int = 40) -> None:
        self.script = script or [match()]
        self.calls: list[tuple[tuple[int, int], object, dict]] = []  # (shape, region, kwargs)
        self.size = size

    class _T:
        def __init__(self, size: int) -> None:
            self.size = size

    @property
    def template(self):
        return FakeMatcher._T(self.size)

    def template_px(self, width: int) -> int:
        return self.size

    def match(self, frame, region=None, **kwargs) -> IconMatch:
        self.calls.append((frame.shape[:2], region, dict(kwargs)))
        i = min(len(self.calls) - 1, len(self.script) - 1)
        return self.script[i]


class FakeClock:
    def __init__(self, t: float = 1000.0) -> None:
        self.t = t
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.sleeps.append(s)
        self.t += s
