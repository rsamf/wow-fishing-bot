"""`wowfish run`: fish until Ctrl-C or the session limit, printing every event."""

from __future__ import annotations

import queue
import time

import typer

from wowfish.audio import AudioUnavailable
from wowfish.commands._common import fail, load_config_or_fail
from wowfish.engine import events as ev
from wowfish.engine.engine import build_engine
from wowfish.engine.thread import EngineThread
from wowfish.errors import NotSupported
from wowfish.gui.presenter import describe


def _line(event: ev.Event) -> str:
    return f"{time.strftime('%H:%M:%S')}  {describe(event)}"


def run(
    minutes: float | None = typer.Option(
        None, "--minutes", min=0.1, help="Stop after this long (default: game.session_minutes)."
    ),
    title: str = typer.Option("World of Warcraft", "--title", help="Window title to drive."),
) -> None:
    """Cast, find the bobber, hear the splash, press Interact, loot, repeat. Ctrl-C stops."""
    cfg = load_config_or_fail()
    try:
        engine = build_engine(cfg, session_s=minutes * 60 if minutes else None, title=title)
    except (RuntimeError, NotSupported, AudioUnavailable) as e:
        fail(str(e))
    thread = EngineThread(engine)
    thread.start()
    w = engine.window
    typer.echo(f"fishing in {w.title!r} ({w.width}x{w.height}); Ctrl-C stops", err=True)
    try:
        while True:
            try:
                event = engine.events.get(timeout=0.2)
            except queue.Empty:
                if not thread.is_alive():
                    break
                continue
            typer.echo(_line(event))
            if isinstance(event, ev.Stopped):
                break
    except KeyboardInterrupt:
        typer.echo("stopping", err=True)
        thread.stop()
        while not engine.events.empty():
            typer.echo(_line(engine.events.get_nowait()))
    typer.echo(engine.stats.as_line())


def register(app: typer.Typer) -> None:
    app.command("run")(run)
