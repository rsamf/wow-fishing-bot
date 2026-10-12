import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_release import (
    check_revision_exists,
    check_tag_matches_version,
    is_prerelease,
)


def test_tag_must_be_v_plus_version():
    check_tag_matches_version("v1.0.0a1", "1.0.0a1")
    with pytest.raises(SystemExit) as exc:
        check_tag_matches_version("v1.0.0a2", "1.0.0a1")
    assert exc.value.code == 1
    with pytest.raises(SystemExit):
        check_tag_matches_version("1.0.0a1", "1.0.0a1")


@pytest.mark.parametrize(
    ("version", "expected"),
    [("1.0.0a1", True), ("1.0.0b3", True), ("1.0.0rc1", True), ("1.0.0", False), ("2.3.1", False)],
)
def test_is_prerelease(version, expected):
    assert is_prerelease(version) is expected


class _Api:
    def __init__(self, exists):
        self._exists = exists

    def revision_exists(self, repo_id, revision, repo_type=None):
        return self._exists


def test_revision_check_passes_and_fails():
    check_revision_exists("r", "abc", api=_Api(True))
    with pytest.raises(SystemExit) as exc:
        check_revision_exists("r", "abc", api=_Api(False))
    assert exc.value.code == 1
