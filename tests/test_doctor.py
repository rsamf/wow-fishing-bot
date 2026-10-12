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


def test_probe_display_on_wayland_without_portal_warns(monkeypatch):
    monkeypatch.setattr(doctor.sys, "platform", "linux")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setattr(doctor, "_screencast_portal_available", lambda: False)
    r = doctor.probe_display()
    assert r.level == "warn"
    assert "wayland" in r.detail and "portal" in r.detail.lower()


def test_probe_display_on_wayland_with_portal_is_ok(monkeypatch):
    monkeypatch.setattr(doctor.sys, "platform", "linux")
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setattr(doctor, "_screencast_portal_available", lambda: True)
    assert doctor.probe_display().level == "ok"


def test_probe_display_on_windows_is_native(monkeypatch):
    monkeypatch.setattr(doctor.sys, "platform", "win32")
    r = doctor.probe_display()
    assert r.level == "ok" and r.detail == "native"


def test_probe_display_on_linux_with_no_display_warns(monkeypatch):
    monkeypatch.setattr(doctor.sys, "platform", "linux")
    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    r = doctor.probe_display()
    assert r.level == "warn" and r.detail == "none"


def test_probe_onnxruntime_ok_with_cpu_provider():
    r = doctor.probe_onnxruntime()
    assert r.level == "ok"
    assert "CPUExecutionProvider" in r.detail


def test_probe_onnxruntime_fails_without_cpu_provider(monkeypatch):
    import onnxruntime

    monkeypatch.setattr(onnxruntime, "get_available_providers", lambda: ["AzureExecutionProvider"])
    r = doctor.probe_onnxruntime()
    assert r.level == "fail"
    assert "CPUExecutionProvider" in r.detail


def test_probe_game_window_is_a_warn_stub():
    r = doctor.probe_game_window()
    assert r.level == "warn" and "not found" in r.detail


def test_probe_models_warns_when_missing_and_names_the_fix():
    r = doctor.probe_models()
    assert r.level == "warn"
    assert "wowfish models pull" in r.detail


def test_probe_models_ok_when_all_cached():
    from wowfish import models

    for spec in models.MODELS:
        p = models.model_path(spec, models.MODEL_REVISION)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
    r = doctor.probe_models()
    assert r.level == "ok" and models.MODEL_REVISION in r.detail


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
    ["system", "display", "onnxruntime", "game window", "models", "config"],
)
def test_default_probes_cover_every_area(name):
    results = doctor.run_probes(doctor.default_probes())
    assert name in [r.name for r in results]
