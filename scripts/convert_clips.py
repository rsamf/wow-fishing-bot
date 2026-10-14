"""Dev-only: convert the game's Vorbis splash clips to 16-bit mono 22050 Hz WAV package assets.

Usage: uv run python scripts/convert_clips.py DIR_WITH_OGG_FILES
Requires ffmpeg on PATH. The WAVs are committed; players never run this.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SOURCES = {
    "sound_spells_fishingbobber_ver2_1.ogg": "fishingbobber_1",
    "sound_spells_fishingbobber_ver2_2.ogg": "fishingbobber_2",
    "sound_spells_fishingbobber_ver2_3.ogg": "fishingbobber_3",
    "sound_spells_tradeskills_fishbite.ogg": "fishbite",
}


def convert(src: Path, dst: Path) -> None:
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", "22050"]
    cmd += ["-sample_fmt", "s16", str(dst)]
    subprocess.run(cmd, check=True)


def main(src_dir: str) -> None:
    out = Path(__file__).resolve().parents[1] / "src" / "wowfish" / "assets" / "clips"
    out.mkdir(parents=True, exist_ok=True)
    for ogg, name in SOURCES.items():
        convert(Path(src_dir) / ogg, out / f"{name}.wav")
        print(f"{ogg} -> {out / (name + '.wav')}")


if __name__ == "__main__":
    main(sys.argv[1])
