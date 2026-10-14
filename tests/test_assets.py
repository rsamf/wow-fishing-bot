import sys
import wave
from pathlib import Path

from wowfish import assets


def test_icon_paths_exist_for_every_native_size():
    assert assets.ICON_SIZES == (29, 42, 53, 79, 103)
    for n in assets.ICON_SIZES:
        p = assets.icon_path(n)
        assert p.is_file(), p
        assert p.name == f"interact_gold_{n}.png"


def test_clip_names_and_families_are_consistent():
    assert set(assets.CLIP_NAMES) == {
        name for names in assets.CLIP_FAMILIES.values() for name in names
    }
    assert set(assets.CLIP_FAMILIES) == {"fishingbobber", "fishbite"}


def test_clips_are_16_bit_mono_22050():
    for name in assets.CLIP_NAMES:
        with wave.open(str(assets.clip_path(name))) as w:
            assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 22050)
            assert 1.5 < w.getnframes() / 22050 < 4.0


def test_asset_dir_follows_pyinstaller_bundle(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert assets.asset_dir() == Path(tmp_path) / "wowfish" / "assets"
