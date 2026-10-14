"""Gain-invariant onset fingerprints and normalized cross-correlation against them."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from wowfish.audio.features import MelParams, log_mel


@dataclass(frozen=True)
class Fingerprint:
    name: str
    feats: np.ndarray  # (L, n_mels), normalized by normalize_block

    @property
    def length(self) -> int:
        return len(self.feats)


def normalize_block(feats: np.ndarray) -> np.ndarray:
    """Remove each frame's mean across bands (gain, flat background), then zero-mean unit-norm."""
    f = feats - feats.mean(axis=-1, keepdims=True)
    f = f - f.mean(axis=(-2, -1), keepdims=True)
    norm = np.sqrt((f * f).sum(axis=(-2, -1), keepdims=True)) + 1e-9
    return f / norm


def build_fingerprint(
    name: str, samples: np.ndarray, p: MelParams, onset_s: float = 0.8
) -> Fingerprint:
    feats = log_mel(samples[: int(onset_s * p.sample_rate)], p)
    if len(feats) < 2:
        raise ValueError(f"clip {name!r} is too short for a {onset_s}s onset fingerprint")
    return Fingerprint(name, normalize_block(feats).astype(np.float32))


def score_sequence(feats: np.ndarray, fp: Fingerprint) -> np.ndarray:
    """NCC of every trailing L-frame window of `feats` with `fp`; -1 before L frames exist."""
    t, length = len(feats), fp.length
    out = np.full(t, -1.0, dtype=np.float32)
    if t < length:
        return out
    windows = sliding_window_view(feats, (length, feats.shape[1]))[:, 0]  # (t-L+1, L, n_mels)
    out[length - 1 :] = np.einsum("tij,ij->t", normalize_block(windows), fp.feats)
    return out
