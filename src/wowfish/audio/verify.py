"""Offline scoring of a recording against every clip, for `verify-bite` and the setup wizard."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from wowfish.audio.clips import family_of
from wowfish.audio.detector import ClipScore
from wowfish.audio.features import DEFAULT_MEL, MelParams, log_mel
from wowfish.audio.fingerprint import Fingerprint, score_sequence
from wowfish.audio.wav import resample


def score_recording(
    samples: np.ndarray,
    rate: int,
    fingerprints: Sequence[Fingerprint],
    p: MelParams = DEFAULT_MEL,
) -> dict[str, np.ndarray]:
    y = resample(np.asarray(samples, dtype=np.float32), rate, p.sample_rate)
    feats = log_mel(y, p)
    return {fp.name: score_sequence(feats, fp) for fp in fingerprints}


def _onset_time(frame: int, fp: Fingerprint, p: MelParams) -> float:
    return (frame * p.hop + p.n_fft) / p.sample_rate - fp.length * p.hop / p.sample_rate


def clip_peaks(
    scores: dict[str, np.ndarray], fingerprints: Sequence[Fingerprint], p: MelParams
) -> list[ClipScore]:
    out = []
    for fp in fingerprints:
        s = scores[fp.name]
        i = int(np.argmax(s))
        out.append(ClipScore(fp.name, float(s[i]), _onset_time(i, fp, p)))
    return out


def noise_floor(
    scores_for_clip: np.ndarray, peak_index: int, p: MelParams, exclude_s: float = 2.0
) -> float:
    """Highest score outside ±exclude_s of the peak: what the clip scores on everything else."""
    half = int(exclude_s / p.frame_s)
    masked = scores_for_clip.copy()
    masked[max(0, peak_index - half) : peak_index + half + 1] = -1.0
    return float(masked.max()) if len(masked) else -1.0


def suggest(
    scores: dict[str, np.ndarray], fingerprints: Sequence[Fingerprint], p: MelParams
) -> tuple[str, float]:
    """(family of the best-scoring clip, threshold halfway between its peak and its noise floor)."""
    best = max(clip_peaks(scores, fingerprints, p), key=lambda c: c.score)
    s = scores[best.name]
    floor = noise_floor(s, int(np.argmax(s)), p)
    threshold = round((best.score + floor) / 2, 2)
    return family_of(best.name), float(min(0.9, max(0.5, threshold)))
