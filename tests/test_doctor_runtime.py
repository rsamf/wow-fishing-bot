from wowfish import doctor, paths
from wowfish.capture import WindowRef

WINDOW = WindowRef("World of Warcraft", 7, 0, 0, 2560, 1440, handle=3)
BIG = WindowRef("World of Warcraft", 7, 0, 0, 4986, 2816, handle=3)


def test_probe_game_window_reports_size_or_not_found(monkeypatch):
    monkeypatch.setattr(doctor, "find_window", lambda title="World of Warcraft": WINDOW)
    r = doctor.probe_game_window()
    assert r.level == "ok" and "2560x1440" in r.detail
    monkeypatch.setattr(doctor, "find_window", lambda title="World of Warcraft": None)
    r = doctor.probe_game_window()
    assert r.level == "warn" and "is the game running" in r.detail


def test_probe_input_on_linux_uses_xtest(monkeypatch):
    monkeypatch.setattr(doctor.sys, "platform", "linux")
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setattr(doctor, "_xtest_available", lambda: (True, "XTest on Xwayland (note)"))
    r = doctor.probe_input()
    assert r.level == "ok" and "XTest" in r.detail
    monkeypatch.setattr(doctor, "_xtest_available", lambda: (False, "XTEST extension missing"))
    assert doctor.probe_input().level == "fail"


def test_probe_input_elsewhere(monkeypatch):
    monkeypatch.setattr(doctor.sys, "platform", "win32")
    assert doctor.probe_input().level == "ok"
    monkeypatch.setattr(doctor.sys, "platform", "darwin")
    r = doctor.probe_input()
    assert r.level == "warn" and "not supported yet" in r.detail


def test_probe_calibration(monkeypatch):
    monkeypatch.setattr(doctor, "find_window", lambda title="World of Warcraft": WINDOW)
    r = doctor.probe_calibration()
    assert r.level == "warn" and "calibrate" in r.detail
    paths.config_file().write_text("[vision]\nicon_size_px = 28\n")
    r = doctor.probe_calibration()
    assert r.level == "ok" and "28 px" in r.detail
    monkeypatch.setattr(doctor, "find_window", lambda title="World of Warcraft": BIG)
    paths.config_file().write_text("[vision]\nicon_size_px = 19\n")
    r = doctor.probe_calibration()
    assert r.level == "fail" and "7 px" in r.detail
    monkeypatch.setattr(doctor, "find_window", lambda title="World of Warcraft": None)
    paths.config_file().write_text("[vision]\nicon_size_px = 56\n")
    r = doctor.probe_calibration()
    assert r.level == "warn" and "56 px" in r.detail


def test_probe_display_checks_x_connection_on_linux(monkeypatch):
    monkeypatch.setattr(doctor.sys, "platform", "linux")
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setattr(doctor, "_x_display_opens", lambda: (True, ""))
    assert doctor.probe_display().level == "ok"
    monkeypatch.setattr(doctor, "_x_display_opens", lambda: (False, "cannot open"))
    assert doctor.probe_display().level == "fail"
    monkeypatch.delenv("DISPLAY", raising=False)
    r = doctor.probe_display()
    assert r.level == "warn" and "DISPLAY" in r.detail


def test_default_probes_include_the_runtime_ones():
    names = [p.__name__ for p in doctor.default_probes()]
    assert names == [
        "probe_system",
        "probe_display",
        "probe_opencv",
        "probe_audio",
        "probe_game_window",
        "probe_input",
        "probe_calibration",
        "probe_config",
    ]
