import platform
import sys

import pytest

from wowfish import doctor, paths


def _ok():
    return doctor.ProbeResult("a", "ok", "fine")


def _warn():
    return doctor.ProbeResult("b", "warn", "meh")


def _boom():
    raise RuntimeError("kaboom")


def test_run_probes_converts_exceptions_into_fail():
    results = doctor.run_probes([_ok, _boom, _warn])
    assert [r.level for r in results] == ["ok", "fail", "warn"]
    assert results[1].name == "_boom"
    assert "kaboom" in results[1].detail


def test_exit_code_is_1_only_when_a_fail_is_present():
    assert doctor.exit_code([_ok(), _warn()]) == 0
    assert doctor.exit_code([_ok(), doctor.ProbeResult("c", "fail", "x")]) == 1


def test_render_is_one_line_per_probe_with_level_first():
    text = doctor.render([_ok(), _warn()])
    assert text.splitlines() == ["ok    a: fine", "warn  b: meh"]


def test_probe_system_reports_os_python_and_version():
    r = doctor.probe_system()
    assert r.level == "ok"
    assert platform.system().lower() in r.detail.lower()
    assert f"{sys.version_info.major}.{sys.version_info.minor}" in r.detail


def test_probe_config_ok_and_fail():
    assert doctor.probe_config().level == "ok"
    paths.config_file().write_text("[game]\ncast_key = \n")
    r = doctor.probe_config()
    assert r.level == "fail" and "line 2" in r.detail


def test_probe_config_warns_on_unknown_keys():
    paths.config_file().write_text("[nope]\nx = 1\n")
    r = doctor.probe_config()
    assert r.level == "warn" and "nope" in r.detail


@pytest.mark.parametrize(
    "name",
    ["system", "display", "opencv", "audio", "game window", "config"],
)
def test_default_probes_cover_every_area(name):
    results = doctor.run_probes(doctor.default_probes())
    assert name in [r.name for r in results]


def test_probe_audio_levels(monkeypatch):
    from wowfish.audio import AudioUnavailable, devices
    from wowfish.audio.devices import LoopbackDevice

    def boom():
        raise AudioUnavailable("no server")

    monkeypatch.setattr(devices, "list_loopback_devices", boom)
    assert doctor.probe_audio().level == "warn"
    monkeypatch.setattr(devices, "list_loopback_devices", lambda: [])
    r = doctor.probe_audio()
    assert r.level == "warn" and "BlackHole" in r.detail
    monkeypatch.setattr(
        devices, "list_loopback_devices", lambda: [LoopbackDevice("m", "Mon", True)]
    )
    r = doctor.probe_audio()
    assert r.level == "ok" and "Mon" in r.detail


def test_probe_opencv_is_ok():
    r = doctor.probe_opencv()
    assert r.level == "ok" and r.detail[0].isdigit()
