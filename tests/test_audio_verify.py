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


def _three_bites(seconds=20.0):
    """Three bobber variants at very different gains, plus pink noise: one session, three bites."""
    from tests.synth_audio import pink_noise

    rng = np.random.default_rng(11)
    y = pink_noise(int(seconds * RATE), rng, rms=0.01)
    for name, at, gain in (
        ("fishingbobber_1", 3.0, 1.0),
        ("fishingbobber_2", 9.0, 0.3),
        ("fishingbobber_3", 15.0, 0.1),
    ):
        clip = CLIPS[name] * gain
        a = int(at * RATE)
        y[a : a + len(clip)] += clip[: len(y) - a]
    return y


def test_family_report_counts_every_bite_and_puts_the_floor_below_them():
    from wowfish.audio.verify import family_report

    scores = score_recording(_three_bites(), RATE, FPS, P)
    report = family_report(scores, FPS, P, "fishingbobber")
    assert report.stands_out
    assert len(report.bites) == 3
    assert sorted(round(b.t) for b in report.bites) == [3, 9, 15]
    assert report.floor < 0.5 < min(b.score for b in report.bites)
    assert 0.5 <= report.threshold <= 0.6
    family, threshold = suggest(scores, FPS, P)
    assert family == "fishingbobber" and threshold == report.threshold


def test_family_report_on_noise_alone_does_not_stand_out():
    from tests.synth_audio import pink_noise
    from wowfish.audio.verify import family_report

    y = pink_noise(int(10 * RATE), np.random.default_rng(12), rms=0.05)
    report = family_report(score_recording(y, RATE, FPS, P), FPS, P, "fishingbobber")
    assert not report.stands_out and report.bites == ()


SESSION2 = "superpowers/spike/session2/listen3.wav"


@pytest.mark.skipif(not __import__("os").path.exists(SESSION2), reason="local recording only")
def test_a_real_five_minute_session_reports_six_bites_and_a_sane_threshold():
    from wowfish.audio.verify import family_report
    from wowfish.audio.wav import read_wav

    y, rate = read_wav(SESSION2)
    report = family_report(score_recording(y, rate, FPS, P), FPS, P, "fishingbobber")
    assert len(report.bites) == 6, [round(b.score, 2) for b in report.bites]
    assert 0.60 <= report.floor <= 0.66
    assert 0.65 <= report.threshold <= 0.71
