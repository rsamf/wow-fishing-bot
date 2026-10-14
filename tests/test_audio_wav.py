import wave

import numpy as np
import pytest

from wowfish.audio.wav import read_wav, resample, write_wav


def _tone(rate, seconds, hz=440.0):
    t = np.arange(int(rate * seconds)) / rate
    return (0.5 * np.sin(2 * np.pi * hz * t)).astype(np.float32)


def test_write_then_read_round_trips_16_bit_mono(tmp_path):
    y = _tone(22050, 0.5)
    write_wav(tmp_path / "a.wav", y, 22050)
    back, rate = read_wav(tmp_path / "a.wav")
    assert rate == 22050 and back.dtype == np.float32 and back.shape == y.shape
    assert np.abs(back - y).max() < 1e-4


def test_stereo_48k_is_downmixed_to_mono_and_keeps_its_rate(tmp_path):
    left, right = _tone(48000, 0.25, 440.0), _tone(48000, 0.25, 880.0)
    inter = np.stack([left, right], axis=1).reshape(-1)
    with wave.open(str(tmp_path / "s.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes((inter * 32767).astype("<i2").tobytes())
    y, rate = read_wav(tmp_path / "s.wav")
    assert rate == 48000 and y.ndim == 1 and len(y) == len(left)
    assert np.abs(y - (left + right) / 2).max() < 1e-3


def test_resample_changes_length_and_keeps_a_tone(tmp_path):
    y = _tone(48000, 1.0, 1000.0)
    z = resample(y, 48000, 22050)
    assert len(z) == 22050
    spectrum = np.abs(np.fft.rfft(z))
    assert abs(np.argmax(spectrum) - 1000) <= 2  # 1 s of audio -> 1 Hz bins
    assert resample(y, 48000, 48000) is y


def test_unsupported_sample_width_is_an_error(tmp_path):
    with wave.open(str(tmp_path / "w.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(5)
        w.setframerate(8000)
        w.writeframes(b"\x00" * 50)
    with pytest.raises(ValueError):
        read_wav(tmp_path / "w.wav")
