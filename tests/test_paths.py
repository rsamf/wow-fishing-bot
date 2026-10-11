from pathlib import Path

from wowfish import paths


def test_wowfish_home_overrides_everything(isolated_home):
    assert paths.config_dir() == isolated_home / "config"
    assert paths.cache_dir() == isolated_home / "cache"
    assert paths.log_dir() == isolated_home / "log"


def test_directories_are_created_on_demand(isolated_home):
    assert not isolated_home.exists()
    d = paths.models_dir()
    assert d.is_dir()
    assert d == isolated_home / "cache" / "models"


def test_file_paths_hang_off_their_dirs(isolated_home):
    assert paths.config_file() == paths.config_dir() / "config.toml"
    assert paths.log_file() == paths.log_dir() / "wowfish.log"


def test_without_override_uses_platformdirs(monkeypatch, tmp_path):
    monkeypatch.delenv("WOWFISH_HOME")
    import platformdirs

    monkeypatch.setattr(platformdirs, "user_config_dir", lambda name: str(tmp_path / "pd-config"))
    assert paths.config_dir() == Path(tmp_path / "pd-config")
