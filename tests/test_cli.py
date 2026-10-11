from wowfish import __version__
from wowfish.cli import app


def test_version_flag_prints_name_and_version(cli_runner):
    result = cli_runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"wowfish {__version__}"


def test_no_args_shows_help_as_usage_error(cli_runner):
    # Click 8.2+ treats a bare invocation as a usage error (exit 2) while printing help.
    result = cli_runner.invoke(app, [])
    assert result.exit_code == 2
    assert "Usage" in result.output
