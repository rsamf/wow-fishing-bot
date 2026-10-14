import sys
import types

import numpy as np
import pytest

from wowfish.audio import AudioSource, AudioUnavailable
from wowfish.audio import devices as dev


class _Mic:
    def __init__(self, id, name, loopback):
        self.id, self.name, self.isloopback = id, name, loopback

    def recorder(self, samplerate, channels, blocksize):
        mic = self

        class _Rec:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *exc):
                return None

            def record(self_inner, numframes):
                return np.full((numframes, channels), 0.25, dtype=np.float32)

        mic.last = (samplerate, channels, blocksize)
        return _Rec()


class _Spk:
    id, name = "alsa_output.hdmi", "HDMI Out"


def _fake_soundcard(monkeypatch, mics):
    fake = types.SimpleNamespace(
        all_microphones=lambda include_loopback=False: mics,
        default_speaker=lambda: _Spk(),
    )
    monkeypatch.setitem(sys.modules, "soundcard", fake)
    return fake


MICS = [
    _Mic("alsa_input.webcam", "Webcam", False),
    _Mic("alsa_output.hdmi.monitor", "Monitor of HDMI Out", True),
    _Mic("bluez_output.x.monitor", "Monitor of Headset", True),
]


def test_lists_only_loopbacks_and_flags_the_default(monkeypatch):
    _fake_soundcard(monkeypatch, MICS)
    found = dev.list_loopback_devices()
    assert [d.name for d in found] == ["Monitor of HDMI Out", "Monitor of Headset"]
    assert [d.is_default for d in found] == [True, False]


def test_open_default_then_by_name_then_by_id(monkeypatch):
    _fake_soundcard(monkeypatch, MICS)
    assert dev.open_loopback().name == "Monitor of HDMI Out"
    assert dev.open_loopback("headset").name == "Monitor of Headset"
    assert dev.open_loopback("bluez_output.x.monitor").name == "Monitor of Headset"
    with pytest.raises(AudioUnavailable):
        dev.open_loopback("nothing like this")


def test_source_reads_mono_float32_at_the_requested_rate(monkeypatch):
    _fake_soundcard(monkeypatch, MICS)
    with dev.open_loopback("headset", sample_rate=22050, blocksize=512) as src:
        assert isinstance(src, AudioSource)
        data = src.read(1000)
        assert data.shape == (1000,) and data.dtype == np.float32 and data[0] == 0.25
    assert MICS[2].last == (22050, 1, 512)


def test_missing_backend_is_audio_unavailable(monkeypatch):
    monkeypatch.setitem(sys.modules, "soundcard", None)  # makes `import soundcard` fail
    with pytest.raises(AudioUnavailable):
        dev.list_loopback_devices()


def test_no_loopback_devices(monkeypatch):
    _fake_soundcard(monkeypatch, [MICS[0]])
    assert dev.list_loopback_devices() == []
    with pytest.raises(AudioUnavailable):
        dev.open_loopback()
