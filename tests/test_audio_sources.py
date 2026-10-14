import wave

import numpy as np

from wowfish.audio import AudioSource, iter_chunks
from wowfish.audio._file import WavFileSource


def _write(path, rate, channels, seconds):
    n = int(rate * seconds)
    data = np.random.default_rng(0).normal(0, 0.1, n * channels).astype(np.float32)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((data * 32767).astype("<i2").tobytes())


def test_wav_source_satisfies_the_protocol_and_resamples(tmp_path):
    _write(tmp_path / "s.wav", 48000, 2, 1.0)
    src = WavFileSource(tmp_path / "s.wav")
    assert isinstance(src, AudioSource)
    assert src.sample_rate == 22050 and len(src.samples) == 22050


def test_read_pads_with_zeros_at_the_end_and_reports_exhaustion(tmp_path):
    _write(tmp_path / "m.wav", 22050, 1, 0.1)  # 2205 samples
    with WavFileSource(tmp_path / "m.wav") as src:
        a = src.read(2000)
        assert a.shape == (2000,) and not src.exhausted
        b = src.read(2000)
        assert b.shape == (2000,) and src.exhausted
        assert (b[205:] == 0).all() and (b[:205] != 0).any()


def test_iter_chunks_counts_time(tmp_path):
    _write(tmp_path / "m.wav", 22050, 1, 0.5)
    src = WavFileSource(tmp_path / "m.wav")
    chunks = []
    for c in iter_chunks(src, 2205):
        chunks.append(c)
        if src.exhausted:
            break
    assert len(chunks) == 5 and chunks[-1].t_end == 0.5 and chunks[-1].sample_rate == 22050
