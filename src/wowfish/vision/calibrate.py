"""One-time measurement of the icon's on-screen size from a screenshot that shows it."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np

from wowfish.vision.matcher import GOLD_MIN, NO_MATCH, IconMatch, IconMatcher
from wowfish.vision.region import Region
from wowfish.vision.template import IconTemplate, template_for_size

PROBE_SIZES: tuple[int, ...] = (20, 32, 48, 72, 104)
MIN_SIZE = 18  # below this the gear is a blob; 1080p draws it at ~21 px, 720p is out of scope
SIZE_PENALTY = 1.0  # chance-level correction: tiny templates score high on any gold ring
ANCHORS = 3
MIN_VALID_SCORE = 0.6


@dataclass(frozen=True)
class Calibration:
    icon_size_px: int
    native_size: int
    score: float
    x: int
    y: int
    gold: float = 0.0

    @property
    def valid(self) -> bool:
        """A gold icon was actually found; otherwise the numbers are the best of nothing."""
        return self.gold >= GOLD_MIN and self.score >= MIN_VALID_SCORE

    def suggested_threshold(self) -> float:
        return float(min(0.9, max(0.6, round(self.score - 0.10, 2))))


def _ranked(m: IconMatch) -> float:
    return m.score if m.gold >= GOLD_MIN else NO_MATCH


def calibrate_icon_scale(
    frame_bgr: np.ndarray,
    templates: Sequence[IconTemplate],
    *,
    sizes: Iterable[int] = range(MIN_SIZE, 128),
    match_width: int = 1920,
    probe_sizes: Sequence[int] = PROBE_SIZES,
    anchors: int = ANCHORS,
) -> Calibration:
    """Locate candidate spots with a few probe sizes, then sweep every size around each.

    Match scores are only comparable across template sizes within a small window, and a tiny
    template scores ~0.8 on any gold ring in the UI, so the sweep runs around the best few
    distinct locations and the winner is the (location, size) with the highest gold-valid score
    after a chance-level penalty of SIZE_PENALTY / size.
    """
    h, w = frame_bgr.shape[:2]
    sizes = list(sizes)
    pad = max(sizes) + 48

    def run(side: int, region: Region | None = None) -> IconMatch:
        return IconMatcher(template_for_size(templates, side), match_width).match(frame_bgr, region)

    probes = sorted((run(s) for s in probe_sizes), key=_ranked, reverse=True)
    spots: list[tuple[int, int]] = []
    for m in probes:
        if _ranked(m) <= NO_MATCH:
            continue
        if all(abs(m.x - ax) > pad or abs(m.y - ay) > pad for ax, ay in spots):
            spots.append((m.x, m.y))
        if len(spots) == anchors:
            break
    if not spots:
        spots = [(w // 2, h // 2)]

    best_side, best, best_key = sizes[0], None, -np.inf
    for ax, ay in spots:
        region = Region(
            max(0.0, (ax - pad) / w),
            max(0.0, (ay - pad) / h),
            min(1.0, (ax + pad) / w),
            min(1.0, (ay + pad) / h),
        )
        for side in sizes:
            m = run(side, region)
            key = _ranked(m) - SIZE_PENALTY / side
            if key > best_key:
                best_side, best, best_key = side, m, key
    assert best is not None
    native = template_for_size(templates, best_side).native_size
    return Calibration(best_side, native, best.score, best.x, best.y, best.gold)
