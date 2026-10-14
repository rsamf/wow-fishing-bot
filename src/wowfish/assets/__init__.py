"""Files shipped inside the package: interact-icon sprites and the game's splash clips."""

from __future__ import annotations

import sys
from pathlib import Path

ICON_SIZES: tuple[int, ...] = (29, 42, 53, 79, 103)
CLIP_FAMILIES: dict[str, tuple[str, ...]] = {
    "fishingbobber": ("fishingbobber_1", "fishingbobber_2", "fishingbobber_3"),
    "fishbite": ("fishbite",),
}
CLIP_NAMES: tuple[str, ...] = tuple(n for names in CLIP_FAMILIES.values() for n in names)


def asset_dir() -> Path:
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        return Path(bundle) / "wowfish" / "assets"
    return Path(__file__).resolve().parent


def icon_path(native_size: int) -> Path:
    return asset_dir() / "interact_icon" / f"interact_gold_{native_size}.png"


def clip_path(name: str) -> Path:
    return asset_dir() / "clips" / f"{name}.wav"
