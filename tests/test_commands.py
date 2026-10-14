import cv2
import numpy as np
import pytest

from tests.synth_audio import RATE, mix
from tests.synth_vision import icon_rgba, paste_icon, water_background
from wowfish import paths
from wowfish.audio import AudioUnavailable
from wowfish.audio.clips import load_reference_clips
from wowfish.audio.devices import LoopbackDevice
from wowfish.audio.wav import write_wav
from wowfish.cli import app
from wowfish.config import load_config


@pytest.fixture
def screenshot(tmp_path):
    frame = water_background(1920, 1080, np.random.default_rng(0))
    paste_icon(frame, icon_rgba(), 48, 900, 400)
    p = tmp_path / "shot.png"
    cv2.imwrite(str(p), frame)
    return p


@pytest.fixture
def bite_wav(tmp_path):
    clips = load_reference_clips()
    rng = np.random.default_rng(3)
    y = mix(clips["fishingbobber_2"], offset_s=2.0, snr_db=20, seconds=6, rng=rng)
    p = tmp_path / "bite.wav"
    write_wav(p, y, RATE)
    return p


def test_calibrate_prints_size_and_saves_config(cli_runner, screenshot):
    result = cli_runner.invoke(app, ["calibrate", str(screenshot)])
    assert result.exit_code == 0, result.output
    assert "icon_size_px=4" in result.output and "native=53" in result.output
    assert "suggested icon_threshold=" in result.output
    assert load_config()[0].vision.icon_size_px == 0
    result = cli_runner.invoke(app, ["calibrate", str(screenshot), "--save"])
    assert result.exit_code == 0
    cfg, _ = load_config()
    assert 45 <= cfg.vision.icon_size_px <= 51 and cfg.vision.icon_native_size == 53
    assert 0.6 <= cfg.vision.icon_threshold <= 0.9


def test_calibrate_rejects_unreadable_image(cli_runner, tmp_path):
    bad = tmp_path / "x.png"
    bad.write_bytes(b"not an image")
    result = cli_runner.invoke(app, ["calibrate", str(bad)])
    assert result.exit_code == 1 and "cannot read" in result.output


def test_watch_from_a_file_calibrates_itself_and_reports_found(cli_runner, screenshot, tmp_path):
    out = tmp_path / "frames"
    args = ["watch", "--from", str(screenshot), "--save-frames", str(out)]
    result = cli_runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert "not calibrated" in result.output
    assert "phase=acquire" in result.output and "FOUND" in result.output
    assert any(out.iterdir())


def test_watch_from_a_directory_tracks_after_acquiring(cli_runner, tmp_path):
    d = tmp_path / "frames"
    d.mkdir()
    for i, cx in enumerate((900, 903, 905)):
        frame = water_background(1920, 1080, np.random.default_rng(i))
        paste_icon(frame, icon_rgba(), 48, cx, 400)
        cv2.imwrite(str(d / f"f{i}.png"), frame)
    paths.config_file().write_text("[vision]\nicon_size_px = 48\nicon_native_size = 53\n")
    result = cli_runner.invoke(app, ["watch", "--from", str(d)])
    assert result.exit_code == 0, result.output
    lines = [line for line in result.output.splitlines() if line.startswith("t=")]
    assert len(lines) == 3
    assert "phase=acquire" in lines[0] and "phase=track" in lines[1] and "phase=track" in lines[2]


def test_watch_needs_a_source(cli_runner):
    result = cli_runner.invoke(app, ["watch"])
    assert result.exit_code == 1 and "--from" in result.output


def test_listen_list_prints_devices_and_marks_the_default(cli_runner, monkeypatch):
    from wowfish.audio import devices

    monkeypatch.setattr(
        devices,
        "list_loopback_devices",
        lambda: [
            LoopbackDevice("a.monitor", "Monitor of A", True),
            LoopbackDevice("b", "B", False),
        ],
    )
    result = cli_runner.invoke(app, ["listen", "--list"])
    assert result.exit_code == 0
    assert "* Monitor of A" in result.output and "  B" in result.output


def test_listen_list_without_backend_exits_0_with_a_message(cli_runner, monkeypatch):
    from wowfish.audio import devices

    def boom():
        raise AudioUnavailable("no pulse")

    monkeypatch.setattr(devices, "list_loopback_devices", boom)
    result = cli_runner.invoke(app, ["listen", "--list"])
    assert result.exit_code == 0 and "no audio backend" in result.output


def test_listen_from_a_wav_reports_the_bite(cli_runner, bite_wav):
    result = cli_runner.invoke(app, ["listen", "--from", str(bite_wav)])
    assert result.exit_code == 0, result.output
    assert "BITE fishingbobber_2" in result.output
    assert "level=" in result.output and "fishbite=" in result.output


def test_listen_from_a_wav_can_record_a_copy(cli_runner, bite_wav, tmp_path):
    out = tmp_path / "copy.wav"
    result = cli_runner.invoke(app, ["listen", "--from", str(bite_wav), "--record", str(out)])
    assert result.exit_code == 0 and out.exists() and f"wrote {out}" in result.output


def test_verify_bite_names_the_family_and_saves(cli_runner, bite_wav):
    result = cli_runner.invoke(app, ["verify-bite", str(bite_wav)])
    assert result.exit_code == 0, result.output
    assert "fishingbobber_2" in result.output and "bite family: fishingbobber" in result.output
    result = cli_runner.invoke(app, ["verify-bite", str(bite_wav), "--save"])
    assert result.exit_code == 0
    cfg, _ = load_config()
    assert cfg.audio.bite_clip == "fishingbobber" and 0.5 <= cfg.audio.bite_threshold <= 0.9


def test_doctor_reports_opencv_and_audio(cli_runner, monkeypatch):
    from wowfish.audio import devices

    monkeypatch.setattr(devices, "list_loopback_devices", lambda: [])
    result = cli_runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert any(line.startswith("ok    opencv:") for line in result.output.splitlines())
    assert any(line.startswith("warn  audio:") for line in result.output.splitlines())


def test_verify_bite_refuses_to_save_when_nothing_stands_out(cli_runner, tmp_path):
    from tests.synth_audio import pink_noise

    p = tmp_path / "noise.wav"
    write_wav(p, pink_noise(6 * RATE, np.random.default_rng(11)), RATE)
    result = cli_runner.invoke(app, ["verify-bite", str(p), "--save"])
    assert result.exit_code == 1 and "no bite stands out" in result.output
    assert load_config()[0].audio.bite_threshold == 0.68


def test_watch_live_without_the_game_fails_cleanly_on_linux(cli_runner, monkeypatch):
    from wowfish import capture

    monkeypatch.setattr(capture, "find_window", lambda title="": None)
    monkeypatch.setattr(capture, "linux_x11", lambda: True)
    result = cli_runner.invoke(app, ["watch", "--live", "--seconds", "1"])
    assert result.exit_code == 1 and "is the game running" in result.output
    assert "Traceback" not in result.output


def test_calibrate_refuses_to_save_without_a_gold_icon(cli_runner, tmp_path):
    from tests.synth_vision import grey_icon_rgba

    frame = water_background(1920, 1080, np.random.default_rng(20))
    paste_icon(frame, grey_icon_rgba(), 48, 900, 400)
    p = tmp_path / "grey.png"
    cv2.imwrite(str(p), frame)
    result = cli_runner.invoke(app, ["calibrate", str(p), "--save"])
    assert result.exit_code == 1 and "not saved" in result.output
    assert load_config()[0].vision.icon_size_px == 0


def test_watch_waits_for_an_icon_before_self_calibrating(cli_runner, tmp_path):
    d = tmp_path / "frames"
    d.mkdir()
    cv2.imwrite(str(d / "f0.png"), water_background(1920, 1080, np.random.default_rng(21)))
    frame = water_background(1920, 1080, np.random.default_rng(22))
    paste_icon(frame, icon_rgba(), 48, 900, 400)
    cv2.imwrite(str(d / "f1.png"), frame)
    result = cli_runner.invoke(app, ["watch", "--from", str(d)])
    assert result.exit_code == 0, result.output
    assert "waiting" in result.output
    assert "FOUND" in result.output
    assert "icon_size_px=127" not in result.output


def test_watch_refuses_an_icon_size_too_small_for_the_window(cli_runner, tmp_path):
    frame = water_background(4986, 2816, np.random.default_rng(0))
    p = tmp_path / "big.png"
    cv2.imwrite(str(p), frame)
    paths.config_file().write_text("[vision]\nicon_size_px = 19\n")
    result = cli_runner.invoke(app, ["watch", "--from", str(p)])
    assert result.exit_code == 1, result.output
    assert "icon_size_px=19" in result.output and "7 px" in result.output
    assert "calibrate" in result.output


def test_run_refuses_when_the_engine_cannot_be_built(cli_runner, monkeypatch):
    from wowfish.commands import run as run_cmd

    def boom(cfg, session_s=None, title="World of Warcraft"):
        raise RuntimeError("the interact icon is not calibrated; run `wowfish calibrate --save`")

    monkeypatch.setattr(run_cmd, "build_engine", boom)
    result = cli_runner.invoke(app, ["run"])
    assert result.exit_code == 1 and "calibrate --save" in result.output


def test_run_prints_events_until_the_engine_stops(cli_runner, monkeypatch):
    from tests.fakes import (
        WINDOW,
        FakeAudio,
        FakeCapturer,
        FakeDetector,
        FakeInput,
        FakeMatcher,
        no_match,
    )
    from wowfish.commands import run as run_cmd
    from wowfish.config import AudioConfig, Config, GameConfig, VisionConfig
    from wowfish.engine.engine import FishingEngine

    def build(cfg, session_s=None, title="World of Warcraft"):
        cfg = Config(
            game=GameConfig(cast_key="8"), vision=VisionConfig(icon_size_px=40), audio=AudioConfig()
        )
        return FishingEngine(
            cfg, WINDOW, capturer=FakeCapturer(), input_device=FakeInput(),
            audio_source=FakeAudio(), detector=FakeDetector(), matcher=FakeMatcher([no_match()]),
            session_s=0.3,
        )  # fmt: skip

    monkeypatch.setattr(run_cmd, "build_engine", build)
    result = cli_runner.invoke(app, ["run", "--minutes", "1"])
    assert result.exit_code == 0, result.output
    assert "Pressed 8 to cast" in result.output
    assert "Stopped (session limit)" in result.output
    assert "casts 1," in result.output.splitlines()[-1]
