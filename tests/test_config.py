import pytest

from wowfish import paths
from wowfish.config import (
    DEFAULT_CONFIG_TEXT,
    AudioConfig,
    Config,
    ConfigError,
    GameConfig,
    VisionConfig,
    ensure_config_file,
    load_config,
    save_config,
    to_toml,
)

DEFAULTS = Config(game=GameConfig(), vision=VisionConfig(), audio=AudioConfig())


def test_missing_file_yields_defaults_and_no_warnings():
    cfg, warnings = load_config()
    assert cfg == DEFAULTS
    assert warnings == []


def test_defaults_match_the_spec():
    assert GameConfig() == GameConfig(cast_key="1", interact_key="f", session_minutes=60)
    assert VisionConfig() == VisionConfig(
        icon_size_px=0, icon_native_size=0, icon_threshold=0.75, match_width=1920
    )
    assert AudioConfig() == AudioConfig(
        device="", bite_clip="fishingbobber", bite_threshold=0.68, refractory_s=3.0
    )


def test_ensure_config_file_creates_with_defaults_once():
    assert ensure_config_file() is True
    assert paths.config_file().read_text() == DEFAULT_CONFIG_TEXT
    assert ensure_config_file() is False


def test_default_text_round_trips_to_defaults():
    paths.config_file().write_text(DEFAULT_CONFIG_TEXT)
    cfg, warnings = load_config()
    assert cfg == DEFAULTS
    assert warnings == []


def test_partial_file_merges_with_defaults():
    paths.config_file().write_text('[game]\ncast_key = "F5"\n[audio]\nbite_threshold = 0.5\n')
    cfg, _ = load_config()
    assert cfg.game.cast_key == "F5"
    assert cfg.game.session_minutes == 60
    assert cfg.audio.bite_threshold == 0.5
    assert cfg.vision == VisionConfig()


def test_unknown_keys_and_old_models_section_warn_but_do_not_fail():
    paths.config_file().write_text('[models]\nrevision = "main"\n[game]\ncast_kee = "2"\n')
    cfg, warnings = load_config()
    assert cfg.game.cast_key == "1"
    assert any("models" in w for w in warnings)
    assert any("game.cast_kee" in w for w in warnings)


def test_integer_is_accepted_for_a_float_field():
    paths.config_file().write_text("[audio]\nbite_threshold = 1\n")
    cfg, _ = load_config()
    assert cfg.audio.bite_threshold == 1.0


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


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("[vision]\nicon_threshold = 0.0\n", "vision.icon_threshold"),
        ("[vision]\nicon_threshold = 1.5\n", "vision.icon_threshold"),
        ("[vision]\nmatch_width = 100\n", "vision.match_width"),
        ("[vision]\nicon_size_px = -1\n", "vision.icon_size_px"),
        ("[audio]\nbite_threshold = 0\n", "audio.bite_threshold"),
        ('[audio]\nbite_clip = "splashy"\n', "audio.bite_clip"),
        ("[audio]\nrefractory_s = -1.0\n", "audio.refractory_s"),
    ],
)
def test_out_of_range_values_are_config_errors(text, key):
    paths.config_file().write_text(text)
    with pytest.raises(ConfigError) as exc:
        load_config()
    assert key in str(exc.value)


def test_to_toml_renders_all_three_tables_in_order():
    text = to_toml(DEFAULTS)
    assert text.index("[game]") < text.index("[vision]") < text.index("[audio]")
    assert 'interact_key = "f"' in text
    assert "icon_threshold = 0.75" in text
    assert 'bite_clip = "fishingbobber"' in text


def test_save_config_round_trips():
    cfg = Config(
        game=GameConfig(cast_key="8"),
        vision=VisionConfig(icon_size_px=56, icon_native_size=79, icon_threshold=0.8),
        audio=AudioConfig(device="Monitor of X", bite_threshold=0.65),
    )
    save_config(cfg)
    loaded, warnings = load_config()
    assert loaded == cfg
    assert warnings == []
