"""Streaming bite detector: feed audio chunks, get a BiteEvent when a trigger onset is heard."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from wowfish.audio import AudioChunk
from wowfish.audio.features import DEFAULT_MEL, MelParams, log_mel
from wowfish.audio.fingerprint import Fingerprint, score_sequence


@dataclass(frozen=True)
class ClipScore:
    name: str
    score: float
    t: float  # stream seconds of the window's onset start


@dataclass(frozen=True)
class BiteEvent:
    clip: str
    score: float
    t: float  # stream seconds of the estimated onset start


class BiteDetector:
    def __init__(
        self,
        fingerprints: Sequence[Fingerprint],
        p: MelParams = DEFAULT_MEL,
        *,
        trigger_clips: Sequence[str],
        threshold: float = 0.7,
        refractory_s: float = 3.0,
        min_consecutive: int = 1,
    ) -> None:
        self.fingerprints = tuple(fingerprints)
        self.p = p
        self.trigger = frozenset(trigger_clips)
        self.threshold = threshold
        self.refractory_s = refractory_s
        self.min_consecutive = min_consecutive
        names = [fp.name for fp in self.fingerprints]
        self._max_len = max(fp.length for fp in self.fingerprints)
        self._pending = np.zeros(0, dtype=np.float32)
        self._feats = np.zeros((0, p.n_mels), dtype=np.float32)
        self._frames_total = 0
        self._run = dict.fromkeys(names, 0)
        self._run_peak = dict.fromkeys(names, 0.0)
        self._scores = {name: ClipScore(name, -1.0, 0.0) for name in names}
        self._level_dbfs = -120.0
        self._quiet_until = -math.inf

    @property
    def last_scores(self) -> tuple[ClipScore, ...]:
        return tuple(self._scores[fp.name] for fp in self.fingerprints)

    @property
    def level_dbfs(self) -> float:
        return self._level_dbfs

    def feed(self, chunk: AudioChunk) -> list[BiteEvent]:
        """Consume a chunk; return every bite heard in it, in time order (usually none or one)."""
        p = self.p
        if chunk.sample_rate != p.sample_rate:
            raise ValueError(
                f"chunk sample rate {chunk.sample_rate} != {p.sample_rate}; "
                "resample in the source, not per chunk"
            )
        samples = np.asarray(chunk.samples, dtype=np.float32)
        if len(samples):
            rms = float(np.sqrt(np.mean(samples * samples)))
            self._level_dbfs = 20.0 * math.log10(rms + 1e-9)
        buf = np.concatenate([self._pending, samples])
        n_new = p.frames_for(len(buf))
        if n_new == 0:
            self._pending = buf
            return []
        new = log_mel(buf[: (n_new - 1) * p.hop + p.n_fft], p)
        self._pending = buf[n_new * p.hop :]
        feats = np.concatenate([self._feats, new])
        self._frames_total += n_new

        # scores[name][j] for the j-th new frame (NaN where fewer than L frames exist yet)
        per_clip: dict[str, np.ndarray] = {}
        for fp in self.fingerprints:
            avail = min(n_new, len(feats) - fp.length + 1)
            col = np.full(n_new, np.nan, dtype=np.float32)
            if avail > 0:
                col[n_new - avail :] = score_sequence(feats[-(avail + fp.length - 1) :], fp)[
                    fp.length - 1 :
                ]
            per_clip[fp.name] = col

        events: list[BiteEvent] = []
        for j in range(n_new):
            frame = self._frames_total - n_new + j  # global index of the window's last frame
            t_end = (frame * p.hop + p.n_fft) / p.sample_rate
            for fp in self.fingerprints:
                score = float(per_clip[fp.name][j])
                if math.isnan(score):
                    continue
                t_onset = t_end - fp.length * p.hop / p.sample_rate
                self._scores[fp.name] = ClipScore(fp.name, score, t_onset)
                if score < self.threshold:
                    self._run[fp.name] = 0
                    self._run_peak[fp.name] = 0.0
                    continue
                self._run[fp.name] += 1
                self._run_peak[fp.name] = max(self._run_peak[fp.name], score)
                fires = (
                    fp.name in self.trigger
                    and self._run[fp.name] == self.min_consecutive
                    and t_end >= self._quiet_until
                )
                if fires:
                    events.append(BiteEvent(fp.name, self._run_peak[fp.name], t_onset))
                    self._quiet_until = t_end + self.refractory_s
        self._feats = feats[-(2 * self._max_len) :]
        return events
