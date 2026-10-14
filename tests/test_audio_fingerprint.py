import numpy as np
import pytest

from wowfish.assets import CLIP_NAMES
from wowfish.audio.clips import ONSET_S, build_fingerprints, family_of, load_reference_clips
from wowfish.audio.features import MelParams, log_mel
from wowfish.audio.fingerprint import normalize_block, score_sequence

P = MelParams()


def test_reference_clips_load_at_22050_mono():
    clips = load_reference_clips()
    assert set(clips) == set(CLIP_NAMES)
    for y in clips.values():
        assert y.dtype == np.float32 and y.ndim == 1 and 1.5 * 22050 < len(y) < 4 * 22050


def test_fingerprints_cover_the_onset_and_are_unit_norm():
    fps = build_fingerprints(P)
    assert [fp.name for fp in fps] == list(CLIP_NAMES)
    expected_len = P.frames_for(int(ONSET_S * P.sample_rate))
    for fp in fps:
        assert fp.length == expected_len and fp.feats.shape == (expected_len, 40)
        assert np.linalg.norm(fp.feats) == pytest.approx(1.0, abs=1e-4)


def test_normalize_block_removes_gain_and_spectral_tilt():
    rng = np.random.default_rng(0)
    f = rng.normal(0, 3, (67, 40)).astype(np.float32)
    assert np.allclose(normalize_block(f), normalize_block(f + 20.0), atol=1e-5)
    tilt = np.linspace(0, 5, 67, dtype=np.float32)[:, None]  # a per-frame offset
    assert np.allclose(normalize_block(f), normalize_block(f + tilt), atol=1e-5)


def test_a_clip_scores_one_against_its_own_onset_and_low_elsewhere():
    clips = load_reference_clips()
    fp = next(f for f in build_fingerprints(P) if f.name == "fishingbobber_2")
    s = score_sequence(log_mel(clips["fishingbobber_2"], P), fp)
    assert s[: fp.length - 1].tolist() == [-1.0] * (fp.length - 1)
    assert s[fp.length - 1] == pytest.approx(1.0, abs=1e-4)
    assert s[fp.length + 30 :].max() < 0.7


def test_families():
    assert family_of("fishingbobber_3") == "fishingbobber" and family_of("fishbite") == "fishbite"
