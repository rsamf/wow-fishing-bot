from pathlib import Path
from unittest.mock import MagicMock

import pytest
from huggingface_hub.errors import (
    LocalEntryNotFoundError,
    RemoteEntryNotFoundError,
    RepositoryNotFoundError,
)

from wowfish import models, paths
from wowfish.config import Config, GameConfig, ModelsConfig


def _cfg(revision=None):
    return Config(game=GameConfig(), models=ModelsConfig(revision=revision))


def test_manifest_has_bobber_and_splash():
    assert [m.role for m in models.MODELS] == ["bobber", "splash"]
    assert [m.filename for m in models.MODELS] == ["bobber.onnx", "splash.onnx"]


def test_effective_revision_prefers_config_override():
    assert models.effective_revision(_cfg()) == models.MODEL_REVISION
    assert models.effective_revision(_cfg("dev")) == "dev"


def test_model_path_is_under_cache_by_revision():
    p = models.model_path(models.MODELS[0], "abc123")
    assert p == paths.models_dir() / "abc123" / "bobber.onnx"


def test_status_reports_missing_then_cached():
    before = models.status("r1")
    assert [s.cached for s in before] == [False, False]
    models.model_path(models.MODELS[0], "r1").parent.mkdir(parents=True)
    models.model_path(models.MODELS[0], "r1").write_bytes(b"x")
    after = models.status("r1")
    assert [s.cached for s in after] == [True, False]


def test_status_treats_empty_file_as_missing():
    p = models.model_path(models.MODELS[1], "r1")
    p.parent.mkdir(parents=True)
    p.write_bytes(b"")
    assert models.status("r1")[1].cached is False


def _fake_downloader(calls):
    def downloader(repo_id, filename, *, revision, local_dir, force_download=False):
        calls.append((repo_id, filename, revision, Path(local_dir), force_download))
        target = Path(local_dir) / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"onnx")
        return str(target)

    return downloader


def test_pull_downloads_each_missing_model_into_revision_dir():
    calls = []
    got = models.pull("r2", downloader=_fake_downloader(calls))
    assert got == [models.model_path(m, "r2") for m in models.MODELS]
    assert [(c[0], c[1], c[2]) for c in calls] == [
        (models.MODEL_REPO, "bobber.onnx", "r2"),
        (models.MODEL_REPO, "splash.onnx", "r2"),
    ]
    assert all(c[3] == paths.models_dir() / "r2" for c in calls)
    assert all(p.read_bytes() == b"onnx" for p in got)


def test_pull_skips_cached_unless_forced():
    calls = []
    models.pull("r3", downloader=_fake_downloader(calls))
    models.pull("r3", downloader=_fake_downloader(calls))
    assert len(calls) == 2
    models.pull("r3", force=True, downloader=_fake_downloader(calls))
    assert len(calls) == 4
    assert all(c[4] is True for c in calls[2:])


def test_pull_wraps_offline_as_network_error():
    def offline(*a, **k):
        raise LocalEntryNotFoundError("cannot find file")

    with pytest.raises(models.ModelDownloadError) as exc:
        models.pull("r4", downloader=offline)
    assert "Could not reach huggingface.co" in str(exc.value)
    assert "wowfish models pull" in str(exc.value)


@pytest.mark.parametrize("err", [RemoteEntryNotFoundError, RepositoryNotFoundError])
def test_pull_wraps_missing_revision_as_packaging_bug(err):
    def missing(*a, **k):
        # Hub HTTP errors require a response object in huggingface_hub 2.x.
        raise err("nope", response=MagicMock(status_code=404, headers={}))

    with pytest.raises(models.ModelDownloadError) as exc:
        models.pull("deadbeef", downloader=missing)
    assert "Model revision deadbeef not found" in str(exc.value)
    assert models.MODEL_REPO in str(exc.value)
    assert "packaging bug" in str(exc.value)


def test_pull_wraps_unexpected_transport_errors_too():
    class ReadError(Exception):  # stands in for httpx2.ReadError, which is not an OSError
        pass

    def flaky(*a, **k):
        raise ReadError("connection reset mid-download")

    with pytest.raises(models.ModelDownloadError) as exc:
        models.pull("r5", downloader=flaky)
    assert "Download of bobber.onnx failed" in str(exc.value)
