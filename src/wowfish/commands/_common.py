"""Helpers shared by the CLI commands."""

from __future__ import annotations

import typer

from wowfish.config import Config, ConfigError, load_config


def fail(message: str) -> None:
    """Print a one-line error and exit 1."""
    typer.echo(f"error: {message}", err=True)
    raise typer.Exit(code=1)


def load_config_or_fail() -> Config:
    try:
        cfg, warnings = load_config()
    except ConfigError as e:
        fail(str(e))
    for w in warnings:
        typer.echo(f"warning: {w}", err=True)
    return cfg
