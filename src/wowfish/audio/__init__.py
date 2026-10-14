"""Audio side of the bot: loopback capture sources and the bite detector."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np


class AudioUnavailable(Exception):
    """No usable audio backend or loopback device on this machine."""


@dataclass(frozen=True)
class AudioChunk:
    samples: np.ndarray  # float32 mono
    sample_rate: int
    t_end: float  # seconds since the source started, at the last sample


@runtime_checkable
class AudioSource(Protocol):
    sample_rate: int

    def __enter__(self) -> AudioSource: ...

    def read(self, n_frames: int) -> np.ndarray:
        """Block until n_frames are available; return float32 mono of exactly that length."""
        ...

    def __exit__(self, *exc: object) -> None: ...


def iter_chunks(source: AudioSource, n_frames: int) -> Iterator[AudioChunk]:
    """Read fixed-size chunks forever (callers break out); t_end counts frames read."""
    total = 0
    while True:
        samples = source.read(n_frames)
        total += len(samples)
        yield AudioChunk(samples, source.sample_rate, total / source.sample_rate)


__all__ = ["AudioChunk", "AudioSource", "AudioUnavailable", "iter_chunks"]
