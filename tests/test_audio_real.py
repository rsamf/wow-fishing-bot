"""Real game audio from a 2026-10-14 loopback capture: two bites, the loudest non-bite sound,
and true silence. These pin behaviour that synthetic mixes cannot: alignment sensitivity,
weak bites, and silence that normalisation would otherwise turn into a 0.6 score."""

import numpy as np
import pytest

from wowfish.assets import CLIP_FAMILIES
from wowfish.audio import AudioChunk
from wowfish.audio.clips import build_fingerprints
from wowfish.audio.detector import BiteDetector
from wowfish.audio.features import DEFAULT_MEL
from wowfish.audio.verify import score_recording
from wowfish.audio.wav import read_wav
from wowfish.config import AudioConfig

FPS = build_fingerprints()
BOBBER_CLIPS = CLIP_FAMILIES["fishingbobber"]
BOBBER = [fp for fp in FPS if fp.name in BOBBER_CLIPS]
THRESHOLD = AudioConfig().bite_threshold
OFFSETS = range(0, 256, 32)  # sub-frame alignments; the detector must not care where a splash lands


def _best(samples, rate, offset):
    scores = score_recording(samples[offset:], rate, BOBBER, DEFAULT_MEL)
    return max(float(s.max()) for s in scores.values())


def _fires(samples, rate, chunk=1024):
    det = BiteDetector(FPS, DEFAULT_MEL, trigger_clips=BOBBER_CLIPS, threshold=THRESHOLD)
    events = []
    for i in range(0, len(samples), chunk):
        block = samples[i : i + chunk]
        events += det.feed(AudioChunk(block, rate, (i + len(block)) / rate))
    return events


def test_a_strong_bite_scores_high_at_every_alignment():
    y, sr = read_wav("tests/fixtures/bite_strong.wav")
    scores = [_best(y, sr, off) for off in OFFSETS]
    assert min(scores) >= 0.88, scores


def test_a_weak_bite_clears_the_default_threshold_at_every_alignment():
    y, sr = read_wav("tests/fixtures/bite_weak.wav")
    scores = [_best(y, sr, off) for off in OFFSETS]
    assert min(scores) >= THRESHOLD + 0.03, scores
    assert len(_fires(y, sr)) == 1


def test_the_loudest_non_bite_sound_stays_well_below_the_threshold():
    y, sr = read_wav("tests/fixtures/nonbite_loud.wav")
    assert max(_best(y, sr, off) for off in OFFSETS) <= THRESHOLD - 0.05
    assert _fires(y, sr) == []


def test_silence_is_gated_and_never_scores():
    y, sr = read_wav("tests/fixtures/silence.wav")
    assert 20 * np.log10(np.sqrt(np.mean(y * y))) < -50  # it really is quiet
    scores = score_recording(y, sr, FPS, DEFAULT_MEL)
    peaks = {k: float(v.max()) for k, v in scores.items()}
    assert all((s == -1.0).all() for s in scores.values()), peaks
    assert _fires(y, sr) == []


def test_default_threshold_sits_between_weak_bites_and_loud_non_bites():
    assert pytest.approx(0.68) == THRESHOLD
