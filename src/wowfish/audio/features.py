"""Log-mel spectrogram frames with numpy only."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np


@dataclass(frozen=True)
class MelParams:
    sample_rate: int = 22050
    n_fft: int = 512
    # 2.9 ms. The onset correlation peak is one hop wide, so at hop 256 (11.6 ms) a real bite's
    # score swung 0.77-0.94 with where the splash fell between frames; at 64 the swing is 0.02.
    hop: int = 64
    n_mels: int = 40
    fmin: float = 300.0
    fmax: float = 8000.0

    @property
    def frame_s(self) -> float:
        return self.hop / self.sample_rate

    def frames_for(self, n_samples: int) -> int:
        if n_samples < self.n_fft:
            return 0
        return 1 + (n_samples - self.n_fft) // self.hop


DEFAULT_MEL = MelParams()

# Mean log-mel of a window below which there is nothing to match. Normalising near-silence
# turns its residual spectrum shape into scores of 0.5-0.6 against every clip, so such windows
# score NO_SCORE instead. In a loopback capture -20 is about -47 dBFS RMS; true silence sits at
# -30 to -40 and the quietest real bite seen so far at about -7.
SILENCE_LEVEL_DB = -20.0


def _hz_to_mel(f: np.ndarray | float) -> np.ndarray | float:
    return 2595.0 * np.log10(1.0 + np.asarray(f) / 700.0)


def _mel_to_hz(m: np.ndarray) -> np.ndarray:
    return 700.0 * (10.0 ** (m / 2595.0) - 1.0)


@lru_cache(maxsize=8)
def mel_filterbank(p: MelParams) -> np.ndarray:
    """(n_mels, n_fft // 2 + 1) triangular filters; every band covers at least one FFT bin."""
    n_bins = p.n_fft // 2 + 1
    mel_points = np.linspace(_hz_to_mel(p.fmin), _hz_to_mel(p.fmax), p.n_mels + 2)
    bins = np.floor((p.n_fft + 1) * _mel_to_hz(mel_points) / p.sample_rate).astype(int)
    bins = np.clip(bins, 0, n_bins - 1)
    fb = np.zeros((p.n_mels, n_bins), dtype=np.float32)
    for i in range(p.n_mels):
        left, centre, right = bins[i], bins[i + 1], bins[i + 2]
        centre = max(centre, left + 1)
        right = max(right, centre + 1)
        fb[i, left:centre] = (np.arange(left, centre) - left) / (centre - left)
        fb[i, centre:right] = (right - np.arange(centre, right)) / (right - centre)
    return fb


@lru_cache(maxsize=4)
def _window(n_fft: int) -> np.ndarray:
    return np.hanning(n_fft).astype(np.float32)


def log_mel(samples: np.ndarray, p: MelParams) -> np.ndarray:
    """(T, n_mels) in dB. T = p.frames_for(len(samples)); zero rows when the input is too short."""
    n = p.frames_for(len(samples))
    if n == 0:
        return np.zeros((0, p.n_mels), dtype=np.float32)
    idx = np.arange(p.n_fft)[None, :] + p.hop * np.arange(n)[:, None]
    frames = np.asarray(samples, dtype=np.float32)[idx] * _window(p.n_fft)
    power = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    return (10.0 * np.log10(power @ mel_filterbank(p).T + 1e-10)).astype(np.float32)
