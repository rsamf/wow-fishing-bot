import numpy as np
import pytest

from tests.synth_audio import RATE, mix
from wowfish.audio.clips import build_fingerprints, load_reference_clips
from wowfish.audio.features import MelParams
from wowfish.audio.verify import clip_peaks, noise_floor, score_recording, suggest

P = MelParams()
FPS = build_fingerprints(P)
CLIPS = load_reference_clips()


def test_scores_peak_at_the_right_clip_and_time():
    rng = np.random.default_rng(0)
    y = mix(CLIPS["fishingbobber_2"], offset_s=4.0, snr_db=20, seconds=10, rng=rng)
    scores = score_recording(y, RATE, FPS, P)
    assert set(scores) == {fp.name for fp in FPS}
    peaks = {cs.name: cs for cs in clip_peaks(scores, FPS, P)}
    best = max(peaks.values(), key=lambda c: c.score)
    assert best.name == "fishingbobber_2" and best.score >= 0.7
    assert best.t == pytest.approx(4.0, abs=0.15)


def test_suggest_picks_the_family_and_a_threshold_between_floor_and_peak():
    rng = np.random.default_rng(1)
    y = mix(CLIPS["fishingbobber_3"], offset_s=2.0, snr_db=20, seconds=8, rng=rng)
    scores = score_recording(y, RATE, FPS, P)
    family, threshold = suggest(scores, FPS, P)
    assert family == "fishingbobber"
    s = scores["fishingbobber_3"]
    peak_i = int(np.argmax(s))
    floor = noise_floor(s, peak_i, P)
    assert floor < threshold < s[peak_i]
    assert 0.5 <= threshold <= 0.9


def test_48k_recordings_are_resampled():
    from wowfish.audio.wav import resample

    rng = np.random.default_rng(2)
    y = mix(CLIPS["fishingbobber_1"], offset_s=1.0, snr_db=20, seconds=4, rng=rng)
    scores = score_recording(resample(y, RATE, 48000), 48000, FPS, P)
    assert scores["fishingbobber_1"].max() >= 0.7
