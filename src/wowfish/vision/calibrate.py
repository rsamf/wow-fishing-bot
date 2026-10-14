"""One-time measurement of the icon's on-screen size from a screenshot that shows it."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np

from wowfish.vision.matcher import GOLD_MIN, NO_MATCH, IconMatch, IconMatcher
from wowfish.vision.region import Region
from wowfish.vision.template import IconTemplate, template_for_size

PROBE_SIZES: tuple[int, ...] = (20, 32, 48, 72, 104)


@dataclass(frozen=True)
class Calibration:
    icon_size_px: int
    native_size: int
    score: float
    x: int
    y: int

    def suggested_threshold(self) -> float:
        return float(min(0.9, max(0.6, round(self.score - 0.10, 2))))


def calibrate_icon_scale(
    frame_bgr: np.ndarray,
    templates: Sequence[IconTemplate],
    *,
    sizes: Iterable[int] = range(14, 128),
    match_width: int = 1920,
    probe_sizes: Sequence[int] = PROBE_SIZES,
) -> Calibration:
    """Locate the icon with a few probe sizes, then sweep every size on a crop around it.

    Match scores are only comparable across template sizes within a small window; on a whole
    frame a tiny template can out-score the true size by chance.
    """
    h, w = frame_bgr.shape[:2]

    def run(side: int, region: Region | None = None) -> IconMatch:
        return IconMatcher(template_for_size(templates, side), match_width).match(frame_bgr, region)

    def ranked(m: IconMatch) -> float:
        return m.score if m.gold >= GOLD_MIN else NO_MATCH

    anchor = max((run(s) for s in probe_sizes), key=ranked)
    sizes = list(sizes)
    pad = max(sizes) + 48
    region = Region(
        max(0.0, (anchor.x - pad) / w),
        max(0.0, (anchor.y - pad) / h),
        min(1.0, (anchor.x + pad) / w),
        min(1.0, (anchor.y + pad) / h),
    )
    fine = {s: run(s, region) for s in sizes}
    best_side = max(fine, key=lambda s: ranked(fine[s]))
    best = fine[best_side]
    native = template_for_size(templates, best_side).native_size
    return Calibration(best_side, native, best.score, best.x, best.y)
