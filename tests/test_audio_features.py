import numpy as np
import pytest

from wowfish.audio.features import MelParams, log_mel, mel_filterbank

P = MelParams()


def test_frames_for_matches_the_framing_rule():
    assert P.frames_for(0) == 0 and P.frames_for(511) == 0 and P.frames_for(512) == 1
    assert P.frames_for(512 + 256 * 10) == 11
    assert P.frame_s == pytest.approx(256 / 22050)


def test_filterbank_shape_and_every_band_is_non_empty():
    fb = mel_filterbank(P)
    assert fb.shape == (40, 257)
    assert (fb.sum(axis=1) > 0).all()


def test_log_mel_shape_and_empty_input():
    y = np.random.default_rng(0).normal(0, 0.1, 22050).astype(np.float32)
    m = log_mel(y, P)
    assert m.shape == (P.frames_for(22050), 40) and m.dtype == np.float32
    assert log_mel(y[:100], P).shape == (0, 40)


def test_a_tone_peaks_in_the_band_that_covers_its_frequency():
    t = np.arange(22050) / 22050
    y = np.sin(2 * np.pi * 1000.0 * t).astype(np.float32)
    m = log_mel(y, P).mean(axis=0)
    fb = mel_filterbank(P)
    centre_hz = (fb * np.linspace(0, 11025, 257)).sum(axis=1) / fb.sum(axis=1)
    assert abs(centre_hz[int(np.argmax(m))] - 1000.0) < 150


def test_gain_is_a_constant_offset_in_the_log_domain():
    y = np.random.default_rng(1).normal(0, 0.05, 22050).astype(np.float32)
    a, b = log_mel(y, P), log_mel(10 * y, P)
    diff = b - a
    assert np.allclose(diff, 20.0, atol=0.05)
