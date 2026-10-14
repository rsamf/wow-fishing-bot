"""Draw a match on a downscaled copy of the very frame it was found in, for the CLI and the GUI."""

from __future__ import annotations

import cv2
import numpy as np

from wowfish.vision.matcher import IconMatch

GREEN = (0, 200, 0)
ORANGE = (0, 140, 255)


def annotate_match(
    frame_bgr: np.ndarray,
    match: IconMatch,
    *,
    thumb_width: int = 480,
    threshold: float | None = None,
) -> np.ndarray:
    h, w = frame_bgr.shape[:2]
    scale = min(1.0, thumb_width / w)
    if scale < 1.0:
        size = (round(w * scale), round(h * scale))
        thumb = cv2.resize(frame_bgr, size, interpolation=cv2.INTER_AREA)
    else:
        thumb = frame_bgr.copy()
    if match.score < 0:
        return thumb
    color = GREEN if (threshold is None or match.accepted(threshold)) else ORANGE
    half = max(2, round(match.size * scale / 2)) + 2
    cx, cy = round(match.x * scale), round(match.y * scale)
    cv2.rectangle(thumb, (cx - half, cy - half), (cx + half, cy + half), color, 2)
    label = f"{match.score:.2f}"
    origin = (cx + half + 4, cy + 4)
    cv2.putText(thumb, label, origin, cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    return thumb
