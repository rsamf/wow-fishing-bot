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


class _SlowSource:
    """Blocks like a real device: `read(n)` returns n frames after n/rate seconds."""

    sample_rate = 22050

    def __init__(self):
        self.entered = self.exited = 0
        self.total = 0

    def __enter__(self):
        self.entered += 1
        return self

    def __exit__(self, *exc):
        self.exited += 1

    def read(self, n):
        import time

        time.sleep(n / self.sample_rate)
        self.total += n
        return np.full(n, 0.25, dtype=np.float32)


def test_threaded_source_never_blocks_the_caller_and_keeps_order():
    import time

    from wowfish.audio._threaded import ThreadedSource

    inner = _SlowSource()
    with ThreadedSource(inner, block=1024) as src:
        assert src.sample_rate == 22050
        t0 = time.monotonic()
        first = src.read(22050)  # a second's worth requested; nothing may be ready yet
        assert time.monotonic() - t0 < 0.05 and len(first) <= 22050
        time.sleep(0.3)
        got = src.read(4096)
        assert 1024 <= len(got) <= 4096 and float(got.mean()) == 0.25
        assert inner.entered == 1
    assert inner.exited == 1


def test_threaded_source_caps_its_backlog():
    import time

    from wowfish.audio._threaded import ThreadedSource

    inner = _SlowSource()
    with ThreadedSource(inner, block=1024, max_s=0.2) as src:
        time.sleep(0.6)
        assert len(src.read(10 * 22050)) <= int(0.2 * 22050) + 1024


def test_recording_source_passes_audio_through_and_writes_a_wav_on_exit(tmp_path):
    from wowfish.audio._recording import RecordingSource
    from wowfish.audio.wav import read_wav

    _write(tmp_path / "m.wav", 22050, 1, 0.2)  # 4410 samples
    inner = WavFileSource(tmp_path / "m.wav")
    out = tmp_path / "heard.wav"
    with RecordingSource(inner, out) as src:
        assert src.sample_rate == 22050 and src.name == inner.__class__.__name__
        a = src.read(3000)
        b = src.read(1410)
        assert not out.exists()
    heard, rate = read_wav(out)
    assert rate == 22050 and len(heard) == 4410
    assert np.allclose(heard, np.concatenate([a, b]), atol=1e-4)


def test_recording_source_writes_nothing_when_nothing_was_read(tmp_path):
    from wowfish.audio._recording import RecordingSource

    _write(tmp_path / "m.wav", 22050, 1, 0.1)
    out = tmp_path / "heard.wav"
    with RecordingSource(WavFileSource(tmp_path / "m.wav"), out):
        pass
    assert not out.exists()
