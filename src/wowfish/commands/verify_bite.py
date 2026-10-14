"""`wowfish verify-bite RECORDING.wav`: which clip family is the bite, and what threshold to use."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Annotated

import numpy as np
import typer

from wowfish import paths
from wowfish.commands._common import load_config_or_fail
from wowfish.config import save_config

MIN_MARGIN = 0.15


def verify_bite(
    recording: Annotated[
        Path,
        typer.Argument(exists=True, dir_okay=False, help="WAV from `wowfish listen --record`."),
    ],
    save: bool = typer.Option(
        False, "--save", help="Write bite_clip and bite_threshold into the config."
    ),
) -> None:
    """Score a recording against every clip; print each clip's peak, floor, and the suggestion."""
    from wowfish.audio.clips import build_fingerprints
    from wowfish.audio.features import MelParams
    from wowfish.audio.verify import clip_peaks, noise_floor, score_recording, suggest
    from wowfish.audio.wav import read_wav

    cfg = load_config_or_fail()
    p = MelParams()
    fps = build_fingerprints(p)
    y, rate = read_wav(recording)
    scores = score_recording(y, rate, fps, p)
    typer.echo(f"{recording}: {len(y) / rate:.1f}s at {rate} Hz")
    for cs in clip_peaks(scores, fps, p):
        s = scores[cs.name]
        floor = noise_floor(s, int(np.argmax(s)), p)
        typer.echo(f"{cs.name:16s} peak {cs.score:5.2f} at {cs.t:6.2f}s   floor {floor:5.2f}")
    family, threshold = suggest(scores, fps, p)
    typer.echo(f"bite family: {family}   suggested bite_threshold={threshold:.2f}")
    best = max(clip_peaks(scores, fps, p), key=lambda c: c.score)
    margin = best.score - noise_floor(scores[best.name], int(np.argmax(scores[best.name])), p)
    if margin < MIN_MARGIN:
        typer.echo(
            f"warning: no clip stands out (peak only {margin:.2f} above its floor); record again "
            "with Ambience and Music at 0 and one clear bite",
            err=True,
        )
        if save:
            typer.echo("not saved", err=True)
            raise typer.Exit(code=1)
    if save:
        audio = replace(cfg.audio, bite_clip=family, bite_threshold=threshold)
        save_config(replace(cfg, audio=audio))
        typer.echo(f"saved to {paths.config_file()}")


def register(app: typer.Typer) -> None:
    app.command("verify-bite")(verify_bite)
