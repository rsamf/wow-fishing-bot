import pytest

from wowfish import paths
from wowfish.config import (
    DEFAULT_CONFIG_TEXT,
    Config,
    ConfigError,
    GameConfig,
    ModelsConfig,
    ensure_config_file,
    load_config,
    to_toml,
)


def test_missing_file_yields_defaults_and_no_warnings():
    cfg, warnings = load_config()
    assert cfg == Config(game=GameConfig(), models=ModelsConfig())
    assert warnings == []


def test_ensure_config_file_creates_with_defaults_once():
    assert ensure_config_file() is True
    assert paths.config_file().read_text() == DEFAULT_CONFIG_TEXT
    assert ensure_config_file() is False


def test_default_text_round_trips_to_defaults():
    paths.config_file().write_text(DEFAULT_CONFIG_TEXT)
    cfg, warnings = load_config()
    assert cfg == Config(game=GameConfig(), models=ModelsConfig())
    assert warnings == []


def test_partial_file_merges_with_defaults():
    paths.config_file().write_text('[game]\ncast_key = "F5"\n')
    cfg, _ = load_config()
    assert cfg.game.cast_key == "F5"
    assert cfg.game.session_minutes == 60


def test_models_revision_override_is_read():
    paths.config_file().write_text('[models]\nrevision = "main"\n')
    cfg, _ = load_config()
    assert cfg.models.revision == "main"


def test_unknown_keys_warn_but_do_not_fail():
    paths.config_file().write_text('[games]\nx = 1\n[game]\ncast_kee = "2"\n')
    cfg, warnings = load_config()
    assert cfg.game.cast_key == "1"
    assert any("games" in w for w in warnings)
    assert any("game.cast_kee" in w for w in warnings)


def test_wrong_type_is_a_config_error_naming_the_key():
    paths.config_file().write_text('[game]\nsession_minutes = "sixty"\n')
    with pytest.raises(ConfigError) as exc:
        load_config()
    assert "game.session_minutes" in str(exc.value)
    assert exc.value.line is None


def test_syntax_error_reports_line_number():
    paths.config_file().write_text("[game]\ncast_key = \n")
    with pytest.raises(ConfigError) as exc:
        load_config()
    assert exc.value.line == 2
    assert str(exc.value).startswith(f"Config error in {paths.config_file()} line 2:")


def test_to_toml_renders_both_tables():
    text = to_toml(Config(game=GameConfig(cast_key="3"), models=ModelsConfig(revision="abc")))
    assert '[game]\ncast_key = "3"\nsession_minutes = 60\n' in text
    assert '[models]\nrevision = "abc"\n' in text


def test_to_toml_omits_none_revision():
    text = to_toml(Config(game=GameConfig(), models=ModelsConfig()))
    assert "revision" not in text
