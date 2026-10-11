from wowfish import __version__, paths
from wowfish.cli import app
from wowfish.config import DEFAULT_CONFIG_TEXT


def test_version_flag_prints_name_and_version(cli_runner):
    result = cli_runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"wowfish {__version__}"


def test_no_args_shows_help_as_usage_error(cli_runner):
    # Click 8.2+ treats a bare invocation as a usage error (exit 2) while printing help.
    result = cli_runner.invoke(app, [])
    assert result.exit_code == 2
    assert "Usage" in result.output


def test_config_path_prints_only_the_path(cli_runner):
    result = cli_runner.invoke(app, ["config", "--path"])
    assert result.exit_code == 0
    assert result.output.strip() == str(paths.config_file())


def test_config_creates_file_and_prints_resolved_toml(cli_runner):
    result = cli_runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert paths.config_file().read_text() == DEFAULT_CONFIG_TEXT
    assert str(paths.config_file()) in result.output
    assert 'cast_key = "1"' in result.output


def test_config_reports_syntax_error_and_exits_1(cli_runner):
    paths.config_file().write_text("[game]\ncast_key = \n")
    result = cli_runner.invoke(app, ["config"])
    assert result.exit_code == 1
    assert "Config error in" in result.output
    assert "line 2" in result.output
    assert "Traceback" not in result.output
