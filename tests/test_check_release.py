import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_release import check_tag_matches_version, is_prerelease


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


def test_main_exits_1_on_mismatched_tag_and_prints_nothing_to_stdout(capsys):
    from check_release import main

    with pytest.raises(SystemExit) as exc:
        main("v9.9.9")
    assert exc.value.code == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert "does not match" in err


def test_assets_check_passes_on_this_tree_and_fails_on_an_empty_one(tmp_path):
    from check_release import check_assets_present

    check_assets_present(Path(__file__).resolve().parents[1])
    with pytest.raises(SystemExit) as exc:
        check_assets_present(tmp_path)
    assert exc.value.code == 1
