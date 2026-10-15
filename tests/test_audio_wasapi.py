"""Per-application capture on Windows: WASAPI process loopback. The COM half only runs on Windows;
the layouts, the sample conversion, and the read loop are checked everywhere."""

import ctypes

import numpy as np
import pytest

from wowfish.audio import AudioSource
from wowfish.audio import _wasapi as wa


def test_activation_params_and_wave_format_have_the_documented_layouts():
    assert ctypes.sizeof(wa.AUDIOCLIENT_ACTIVATION_PARAMS) == 12
    assert ctypes.sizeof(wa.WAVEFORMATEX) == 18
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        assert ctypes.sizeof(wa.PROPVARIANT) == 24
    params = wa.activation_params(4242)
    assert params.ActivationType == wa.AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK == 1
    assert params.ProcessLoopbackParams.TargetProcessId == 4242
    assert params.ProcessLoopbackParams.ProcessLoopbackMode == 0  # include the process tree


def test_guid_round_trips_the_registry_text():
    g = wa.GUID.from_text("1CB9AD4C-DBFA-4c32-B178-C2F568A703B2")
    assert bytes(g).hex() == "4cadb91cfadb324cb178c2f568a703b2"
    assert ctypes.sizeof(g) == 16


def test_capture_format_is_44100_hz_stereo_16_bit_pcm_as_in_the_microsoft_sample():
    f = wa.capture_format()
    assert (f.wFormatTag, f.nChannels, f.nSamplesPerSec, f.wBitsPerSample) == (1, 2, 44100, 16)
    assert f.nBlockAlign == 4 and f.nAvgBytesPerSec == 44100 * 4


def test_pcm_frames_become_mono_float32_at_22050():
    left = np.array([0, 16384, -16384, 32767], dtype="<i2")
    right = np.array([0, 0, 0, 32767], dtype="<i2")
    raw = np.stack([left, right], axis=1).tobytes()  # 4 stereo frames at 44100
    out = wa.to_mono_22050(raw)
    assert out.dtype == np.float32 and out.shape == (2,)
    assert out[0] == pytest.approx((0 + 0 + 16384 + 0) / 2 / 2 / 32768.0)
    assert out[1] == pytest.approx(((-16384 + 0) / 2 + (32767 + 32767) / 2) / 2 / 32768.0)


class _FakeBackend:
    """Packets of 44100 Hz stereo int16; None means "nothing yet"; SILENT packets are zeros."""

    def __init__(self, packets):
        self.packets = list(packets)
        self.opened = self.closed = False

    def open(self):
        self.opened = True

    def read_packet(self):
        return self.packets.pop(0) if self.packets else None

    def close(self):
        self.closed = True


def _packet(frames, value):
    return np.full(frames * 2, value, dtype="<i2").tobytes()


def test_source_accumulates_packets_until_the_requested_frames_exist():
    backend = _FakeBackend([_packet(1000, 3276), None, _packet(3000, 3276), _packet(96, 3276)])
    src = wa.ProcessLoopbackSource(4242, backend=backend)
    assert isinstance(src, AudioSource) and src.sample_rate == 22050
    assert src.name == "process 4242 (game audio only)"
    with src:
        assert backend.opened
        a = src.read(1024)  # 1024 mono frames at 22050 = 2048 stereo frames at 44100
        b = src.read(1024)
        assert a.shape == b.shape == (1024,)
        assert float(a.mean()) == pytest.approx(0.1, abs=1e-3)
    assert backend.closed


def test_source_gives_up_when_no_packet_arrives_for_too_long():
    src = wa.ProcessLoopbackSource(1, backend=_FakeBackend([]), timeout_s=0.05)
    with src, pytest.raises(RuntimeError) as exc:
        src.read(10)
    assert "no audio" in str(exc.value)
