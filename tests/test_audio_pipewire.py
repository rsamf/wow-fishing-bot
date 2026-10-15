"""Per-application capture on Linux: find the game's PipeWire stream, record it with pw-record."""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

from wowfish.audio import AudioSource, AudioUnavailable
from wowfish.audio import _pipewire as pw

DUMP = Path("tests/fixtures/pw_dump.json").read_text()


def test_lists_only_application_output_streams():
    streams = pw.list_app_streams(dump=lambda: DUMP)
    assert [(s.serial, s.name, s.pid) for s in streams] == [
        (3129, "World of Warcraft", 935841),
        (3300, "Firefox", 5555),
    ]


def test_picks_by_pid_first_then_by_name_case_insensitively():
    streams = pw.list_app_streams(dump=lambda: DUMP)
    assert pw.pick_stream(streams, pid=935841, name="nothing").serial == 3129
    assert pw.pick_stream(streams, pid=1, name="world of WARCRAFT").serial == 3129
    assert pw.pick_stream(streams, pid=None, name="firefox").serial == 3300
    assert pw.pick_stream(streams, pid=None, name="Spotify") is None


def test_unparseable_dump_is_audio_unavailable():
    with pytest.raises(AudioUnavailable) as exc:
        pw.list_app_streams(dump=lambda: "not json")
    assert "pw-dump" in str(exc.value)


# A stand-in for pw-record: writes `frames` float32 samples of 0.25 to stdout, then exits.
_FAKE_RECORD = [
    sys.executable,
    "-c",
    "import sys, numpy as np; sys.stdout.buffer.write(np.full(5000, 0.25, np.float32).tobytes())",
]


def test_source_reads_exact_mono_float32_blocks_from_the_recorder():
    src = pw.PipewireAppSource(3129, "World of Warcraft", command=_FAKE_RECORD)
    assert isinstance(src, AudioSource)
    assert src.sample_rate == 22050 and src.name == "World of Warcraft (game audio only)"
    with src:
        a = src.read(1024)
        b = src.read(3976)
        assert a.shape == (1024,) and a.dtype == np.float32 and float(a.mean()) == 0.25
        assert b.shape == (3976,)
        with pytest.raises(RuntimeError) as exc:  # the stream ended: 5000 frames were all of it
            src.read(1024)
        assert "ended" in str(exc.value)


def test_default_command_targets_the_serial_and_asks_for_raw_mono_float():
    src = pw.PipewireAppSource(3129, "World of Warcraft", sample_rate=22050)
    cmd = src.command
    assert cmd[0] == "pw-record" and "--target" in cmd and "3129" in cmd
    assert cmd[cmd.index("--rate") + 1] == "22050"
    assert cmd[cmd.index("--channels") + 1] == "1"
    assert cmd[cmd.index("--format") + 1] == "f32"
    assert "--raw" in cmd and cmd[-1] == "-"


def test_open_app_stream_needs_pw_record(monkeypatch):
    monkeypatch.setattr(pw.shutil, "which", lambda name: None)
    with pytest.raises(AudioUnavailable) as exc:
        pw.open_app_stream(pid=1, name="World of Warcraft", dump=lambda: DUMP)
    assert "pw-record" in str(exc.value)


def test_open_app_stream_explains_a_missing_game_stream(monkeypatch):
    monkeypatch.setattr(pw.shutil, "which", lambda name: "/usr/bin/pw-record")
    with pytest.raises(AudioUnavailable) as exc:
        pw.open_app_stream(pid=1, name="Spotify", dump=lambda: DUMP)
    msg = str(exc.value)
    assert "no audio stream from 'Spotify'" in msg and 'audio.capture = "device"' in msg


def test_open_app_stream_returns_a_source_for_the_game(monkeypatch):
    monkeypatch.setattr(pw.shutil, "which", lambda name: "/usr/bin/pw-record")
    src = pw.open_app_stream(pid=935841, name="World of Warcraft", dump=lambda: DUMP)
    assert src.serial == 3129 and src.name.startswith("World of Warcraft")


def test_real_dump_runner_is_pw_dump():
    assert pw.PW_DUMP == ["pw-dump"]
    assert json.loads(DUMP)[1]["id"] == 90  # the fixture is a trimmed real dump
