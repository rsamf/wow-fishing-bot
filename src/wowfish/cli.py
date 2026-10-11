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
