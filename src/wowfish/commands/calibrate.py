"""`wowfish calibrate SCREENSHOT`: measure the interact icon's on-screen size once."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Annotated

import typer

from wowfish import paths
from wowfish.commands._common import fail, load_config_or_fail
from wowfish.config import save_config


def calibrate(
    screenshot: Annotated[
        Path,
        typer.Argument(exists=True, dir_okay=False, help="Screenshot showing the gold gear icon."),
    ],
    save: bool = typer.Option(False, "--save", help="Write the result into the config file."),
) -> None:
    """Find the interact icon in a screenshot and report its size, position, and a threshold."""
    import cv2

    from wowfish.vision.calibrate import calibrate_icon_scale
    from wowfish.vision.template import load_icon_templates

    cfg = load_config_or_fail()
    frame = cv2.imread(str(screenshot))
    if frame is None:
        fail(f"cannot read image {screenshot}")
    cal = calibrate_icon_scale(frame, load_icon_templates(), match_width=cfg.vision.match_width)
    h, w = frame.shape[:2]
    typer.echo(
        f"icon_size_px={cal.icon_size_px} native={cal.native_size} score={cal.score:.3f} "
        f"at ({cal.x}, {cal.y}) in {w}x{h}"
    )
    threshold = cal.suggested_threshold()
    typer.echo(f"suggested icon_threshold={threshold:.2f}")
    if cal.score < 0.6:
        typer.echo(
            "warning: low score; is the gold interact icon visible in this screenshot?", err=True
        )
    if save:
        vision = replace(
            cfg.vision,
            icon_size_px=cal.icon_size_px,
            icon_native_size=cal.native_size,
            icon_threshold=threshold,
        )
        save_config(replace(cfg, vision=vision))
        typer.echo(f"saved to {paths.config_file()}")


def register(app: typer.Typer) -> None:
    app.command("calibrate")(calibrate)
