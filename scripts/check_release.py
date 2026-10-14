"""Preflight for release.yml. Fails fast before anything is built.

Usage: uv run python scripts/check_release.py TAG
Prints `prerelease=true|false` on success.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

_PRERELEASE_RE = re.compile(r"^\d+(\.\d+)*(a|b|rc)\d+")


def check_tag_matches_version(tag: str, version: str) -> None:
    if tag != f"v{version}":
        print(f"error: tag {tag!r} does not match pyproject version {version!r}", file=sys.stderr)
        raise SystemExit(1)


def is_prerelease(version: str) -> bool:
    return bool(_PRERELEASE_RE.match(version))


def check_assets_present(root: Path) -> None:
    assets = root / "src" / "wowfish" / "assets"
    expected = [assets / "interact_icon" / f"interact_gold_{n}.png" for n in (29, 42, 53, 79, 103)]
    clips = ("fishingbobber_1", "fishingbobber_2", "fishingbobber_3", "fishbite")
    expected += [assets / "clips" / f"{n}.wav" for n in clips]
    missing = [str(p.relative_to(root)) for p in expected if not p.is_file()]
    if missing:
        print(f"error: missing package assets: {', '.join(missing)}", file=sys.stderr)
        raise SystemExit(1)


def main(tag: str) -> None:
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    check_tag_matches_version(tag, version)
    check_assets_present(root)
    print(f"prerelease={'true' if is_prerelease(version) else 'false'}")


if __name__ == "__main__":
    main(sys.argv[1])
