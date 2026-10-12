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


models_app = typer.Typer(help="Download and inspect model weights.", no_args_is_help=True)
app.add_typer(models_app, name="models")


def _human_size(n: int) -> str:
    for unit in ("B", "KB", "MB"):
        if n < 1024:
            return f"{n} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n //= 1024
    return f"{n} GB"


def _load_config_or_fail():
    from wowfish import paths
    from wowfish.config import ConfigError, load_config

    try:
        cfg, warnings = load_config(paths.config_file())
    except ConfigError as e:
        fail(str(e))
    for w in warnings:
        typer.echo(f"warning: {w}", err=True)
    return cfg


@models_app.command("status")
def models_status() -> None:
    """Show the pinned model revision and which files are cached."""
    from wowfish import models

    cfg = _load_config_or_fail()
    revision = models.effective_revision(cfg)
    note = " (override from config)" if cfg.models.revision else ""
    typer.echo(f"repo:     {models.MODEL_REPO}")
    typer.echo(f"revision: {revision}{note}")
    for st in models.status(revision):
        state = "cached" if st.cached else "missing"
        typer.echo(f"{st.spec.filename:<14} {state:<8} {st.path}")


@models_app.command("pull")
def models_pull(
    force: bool = typer.Option(False, "--force", help="Re-download even if cached."),
) -> None:
    """Download model weights from the Hugging Face Hub."""
    from wowfish import models

    cfg = _load_config_or_fail()
    revision = models.effective_revision(cfg)
    try:
        for p in models.pull(revision, force=force, downloader=models.hf_hub_download):
            typer.echo(f"{p.name:<14} {_human_size(p.stat().st_size)}")
    except models.ModelDownloadError as e:
        fail(str(e))
