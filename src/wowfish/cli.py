"""Command-line entry point. Subcommands are registered by other modules."""

from __future__ import annotations

import typer

from wowfish import __version__

app = typer.Typer(
    name="wowfish",
    help="A vision-based fishing bot for World of Warcraft: Forever.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"wowfish {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Print the version and exit.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    from wowfish.logging import setup_logging

    setup_logging(verbose=verbose)


def main() -> None:
    app()


def fail(message: str) -> None:
    """Print a one-line error and exit 1. Used by every command."""
    typer.echo(f"error: {message}", err=True)
    raise typer.Exit(code=1)


@app.command()
def config(
    path_only: bool = typer.Option(False, "--path", help="Print only the config file path."),
) -> None:
    """Show the config file location and its resolved contents."""
    from wowfish import paths
    from wowfish.config import ConfigError, ensure_config_file, load_config, to_toml

    cfg_path = paths.config_file()
    if path_only:
        typer.echo(str(cfg_path))
        return
    if ensure_config_file(cfg_path):
        typer.echo(f"created {cfg_path} with defaults")
    try:
        cfg, warnings = load_config(cfg_path)
    except ConfigError as e:
        fail(str(e))
    for w in warnings:
        typer.echo(f"warning: {w}", err=True)
    typer.echo(f"# {cfg_path}")
    typer.echo(to_toml(cfg), nl=False)


@app.command()
def doctor() -> None:
    """Check this machine: display, OpenCV, audio, config. Exits 1 only on hard failures."""
    from wowfish import doctor as doc

    results = doc.run_probes(doc.default_probes())
    typer.echo(doc.render(results))
    raise typer.Exit(code=doc.exit_code(results))
