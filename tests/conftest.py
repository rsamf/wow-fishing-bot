import pytest
from typer.testing import CliRunner


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Point every wowfish path at a throwaway directory."""
    home = tmp_path / "wowfish-home"
    monkeypatch.setenv("WOWFISH_HOME", str(home))
    return home


@pytest.fixture
def cli_runner():
    return CliRunner()
