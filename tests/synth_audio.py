"""Synthetic recordings for detector tests: reference clips mixed into pink noise."""

from __future__ import annotations

import numpy as np

RATE = 22050


def pink_noise(n: int, rng: np.random.Generator, rms: float = 0.05) -> np.ndarray:
    white = rng.normal(0, 1, n)
    spectrum = np.fft.rfft(white)
    freqs = np.fft.rfftfreq(n)
    spectrum[1:] /= np.sqrt(freqs[1:])
    pink = np.fft.irfft(spectrum, n)
    return (pink / (np.sqrt(np.mean(pink**2)) + 1e-12) * rms).astype(np.float32)


def mix(
    clip: np.ndarray,
    *,
    offset_s: float,
    snr_db: float,
    seconds: float,
    rng: np.random.Generator,
    gain: float = 1.0,
    distractor: np.ndarray | None = None,
    distractor_offset_s: float | None = None,
) -> np.ndarray:
    """Pink noise `seconds` long with `clip` placed at `offset_s` at `snr_db` above the noise."""
    out = pink_noise(int(seconds * RATE), rng)
    noise_rms = float(np.sqrt(np.mean(out**2)))
    for y, off in ((clip, offset_s), (distractor, distractor_offset_s)):
        if y is None or off is None:
            continue
        y_rms = float(np.sqrt(np.mean(y**2))) + 1e-12
        scaled = y * (noise_rms * 10 ** (snr_db / 20) / y_rms)
        start = int(off * RATE)
        end = min(len(out), start + len(scaled))
        out[start:end] += scaled[: end - start]
    return (out * gain).astype(np.float32)
