import numpy as np
import pytest

from tests.synth_audio import RATE, mix, pink_noise
from wowfish.assets import CLIP_FAMILIES
from wowfish.audio import AudioChunk
from wowfish.audio.clips import build_fingerprints, load_reference_clips
from wowfish.audio.detector import BiteDetector
from wowfish.audio.features import MelParams

P = MelParams()
FPS = build_fingerprints(P)
CLIPS = load_reference_clips()
BOBBER = CLIP_FAMILIES["fishingbobber"]


def run(detector, y, chunk=1024):
    events = []
    for i in range(0, len(y), chunk):
        part = y[i : i + chunk]
        ev = detector.feed(AudioChunk(part, RATE, (i + len(part)) / RATE))
        if ev:
            events.append(ev)
    return events


def make(**kw):
    return BiteDetector(FPS, P, trigger_clips=BOBBER, **kw)


@pytest.mark.parametrize("name", BOBBER)
@pytest.mark.parametrize(("snr_db", "gain"), [(20, 1.0), (10, 0.05), (10, 1.0)])
def test_detects_each_bobber_variant_in_pink_noise(name, snr_db, gain):
    rng = np.random.default_rng(7)
    y = mix(CLIPS[name], offset_s=3.0, snr_db=snr_db, seconds=8, rng=rng, gain=gain)
    events = run(make(), y)
    assert len(events) == 1, events
    assert events[0].clip == name and events[0].score >= 0.7
    assert events[0].t == pytest.approx(3.0, abs=0.15)


def test_noise_alone_never_fires_and_scores_stay_low():
    det = make()
    assert run(det, pink_noise(20 * RATE, np.random.default_rng(3))) == []
    assert max(s.score for s in det.last_scores) < 0.6


def test_fishbite_is_scored_but_does_not_trigger_the_bobber_family():
    y = mix(CLIPS["fishbite"], offset_s=2.0, snr_db=20, seconds=6, rng=np.random.default_rng(1))
    det = make()
    assert run(det, y) == []
    det2 = BiteDetector(FPS, P, trigger_clips=CLIP_FAMILIES["fishbite"])
    events = run(det2, y)
    assert len(events) == 1 and events[0].clip == "fishbite"


def test_families_do_not_cross_trigger():
    # the bite family must not fire on the other family's sound, and vice versa
    y = mix(CLIPS["fishbite"], offset_s=2.0, snr_db=25, seconds=6, rng=np.random.default_rng(2))
    assert run(make(), y) == []
    for name in BOBBER:
        y = mix(CLIPS[name], offset_s=2.0, snr_db=25, seconds=6, rng=np.random.default_rng(4))
        assert run(BiteDetector(FPS, P, trigger_clips=CLIP_FAMILIES["fishbite"]), y) == []


def test_gain_does_not_move_the_score():
    rng = np.random.default_rng(5)
    y = mix(CLIPS["fishingbobber_1"], offset_s=2.0, snr_db=20, seconds=5, rng=rng)
    a = run(make(), y)[0]
    b = run(make(), 10 * y)[0]
    assert abs(a.score - b.score) < 0.02 and a.t == b.t


def test_chunk_size_does_not_change_the_result():
    rng = np.random.default_rng(6)
    y = mix(CLIPS["fishingbobber_3"], offset_s=1.5, snr_db=20, seconds=4, rng=rng)
    big = run(make(), y, chunk=len(y))
    small = run(make(), y, chunk=37)
    assert len(big) == len(small) == 1
    assert big[0].clip == small[0].clip
    assert big[0].t == pytest.approx(small[0].t, abs=1e-6)
    assert big[0].score == pytest.approx(small[0].score, abs=1e-3)  # batch FFT rounding


def test_refractory_suppresses_a_second_bite_but_not_a_later_one():
    rng = np.random.default_rng(8)
    c = CLIPS["fishingbobber_2"]
    close = mix(
        c, offset_s=1.0, snr_db=20, seconds=6, rng=rng, distractor=c, distractor_offset_s=2.5
    )
    assert len(run(make(refractory_s=3.0), close)) == 1
    far = mix(c, offset_s=1.0, snr_db=20, seconds=8, rng=rng, distractor=c, distractor_offset_s=5.0)
    assert len(run(make(refractory_s=3.0), far)) == 2


def test_level_tracks_the_last_chunk():
    det = make()
    det.feed(AudioChunk(np.zeros(2205, np.float32), RATE, 0.1))
    assert det.level_dbfs < -100
    det.feed(AudioChunk(np.full(2205, 0.5, np.float32), RATE, 0.2))
    assert det.level_dbfs == pytest.approx(20 * np.log10(0.5), abs=0.1)


def test_48k_chunks_are_resampled_on_the_way_in():
    from wowfish.audio.wav import resample

    rng = np.random.default_rng(9)
    y = mix(CLIPS["fishingbobber_1"], offset_s=2.0, snr_db=20, seconds=5, rng=rng)
    y48 = resample(y, RATE, 48000)
    det = make()
    events = []
    for i in range(0, len(y48), 2048):
        part = y48[i : i + 2048]
        ev = det.feed(AudioChunk(part, 48000, (i + len(part)) / 48000))
        if ev:
            events.append(ev)
    assert len(events) == 1 and events[0].t == pytest.approx(2.0, abs=0.15)
