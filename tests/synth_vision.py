"""Synthetic fishing frames for vision tests: water-like backgrounds with a pasted gear icon."""

from __future__ import annotations

import cv2
import numpy as np

from wowfish.assets import icon_path


def water_background(width: int, height: int, rng: np.random.Generator) -> np.ndarray:
    y = np.linspace(0, 1, height, dtype=np.float32)[:, None]
    base = np.stack([70 + 40 * y, 60 + 30 * y, 45 + 20 * y], axis=-1)  # BGR, dark blue water
    base = np.broadcast_to(base, (height, width, 3)).copy()
    ripples = rng.normal(0, 12, size=(height // 4, width // 4, 1)).astype(np.float32)
    ripples = cv2.resize(ripples, (width, height), interpolation=cv2.INTER_LINEAR)[..., None]
    xs = np.arange(width, dtype=np.float32)[None, :, None]
    waves = 10 * np.sin(xs / 37.0 + 3 * y[..., None])
    return np.clip(base + ripples + waves, 0, 255).astype(np.uint8)


def icon_rgba(native: int = 79) -> np.ndarray:
    return cv2.imread(str(icon_path(native)), cv2.IMREAD_UNCHANGED)


def grey_icon_rgba(native: int = 79) -> np.ndarray:
    """The out-of-range look: same shape, no colour, a little darker."""
    rgba = icon_rgba(native).copy()
    grey = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_BGR2GRAY)
    grey = (grey.astype(np.float32) * 0.55).astype(np.uint8)
    rgba[:, :, :3] = np.stack([grey, grey, grey], axis=-1)
    return rgba


def paste_icon(
    frame: np.ndarray, rgba: np.ndarray, side: int, cx: int, cy: int, brightness: float = 1.0
) -> np.ndarray:
    """Alpha-composite the sprite at `side` px centred on (cx, cy). Returns the same array."""
    icon = cv2.resize(rgba, (side, side), interpolation=cv2.INTER_AREA)
    bgr = np.clip(icon[:, :, :3].astype(np.float32) * brightness, 0, 255)
    alpha = icon[:, :, 3:4].astype(np.float32) / 255.0
    x0, y0 = cx - side // 2, cy - side // 2
    roi = frame[y0 : y0 + side, x0 : x0 + side].astype(np.float32)
    frame[y0 : y0 + side, x0 : x0 + side] = (roi * (1 - alpha) + bgr * alpha).astype(np.uint8)
    return frame
