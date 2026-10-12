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


def check_revision_exists(repo: str, revision: str, api=None) -> None:
    if api is None:
        from huggingface_hub import HfApi

        api = HfApi()
    if not api.revision_exists(repo, revision, repo_type="model"):
        print(f"error: model revision {revision} not found in {repo}", file=sys.stderr)
        raise SystemExit(1)


def main(tag: str) -> None:
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    check_tag_matches_version(tag, version)
    sys.path.insert(0, str(root / "src"))
    from wowfish.models import MODEL_REPO, MODEL_REVISION

    check_revision_exists(MODEL_REPO, MODEL_REVISION)
    print(f"prerelease={'true' if is_prerelease(version) else 'false'}")


if __name__ == "__main__":
    main(sys.argv[1])
