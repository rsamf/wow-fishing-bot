"""Model weights: what we need, where they live, and how to fetch them from the Hub.

The revision is pinned per release so a model update on the Hub can never change
the behavior of an already-shipped binary.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from huggingface_hub import hf_hub_download
from huggingface_hub.errors import (
    EntryNotFoundError,
    HfHubHTTPError,
    LocalEntryNotFoundError,
    RepositoryNotFoundError,
    RevisionNotFoundError,
)

from wowfish import paths
from wowfish.config import Config

MODEL_REPO = "rsamf/wow-fishing-forever"
# Replaced with a full commit hash once the Hub repo exists (see release checklist).
MODEL_REVISION = "main"

Downloader = Callable[..., str]


@dataclass(frozen=True)
class ModelSpec:
    role: str
    filename: str


MODELS: tuple[ModelSpec, ...] = (
    ModelSpec("bobber", "bobber.onnx"),
    ModelSpec("splash", "splash.onnx"),
)


@dataclass(frozen=True)
class ModelStatus:
    spec: ModelSpec
    path: Path
    cached: bool


class ModelDownloadError(Exception):
    pass


def effective_revision(cfg: Config) -> str:
    return cfg.models.revision or MODEL_REVISION


def model_path(spec: ModelSpec, revision: str) -> Path:
    return paths.models_dir() / revision / spec.filename


def status(revision: str) -> list[ModelStatus]:
    out = []
    for spec in MODELS:
        p = model_path(spec, revision)
        cached = p.is_file() and p.stat().st_size > 0
        out.append(ModelStatus(spec, p, cached))
    return out


def pull(
    revision: str, *, force: bool = False, downloader: Downloader = hf_hub_download
) -> list[Path]:
    """Download every model file at `revision`. Returns the local paths in manifest order."""
    local_dir = paths.models_dir() / revision
    results: list[Path] = []
    for st in status(revision):
        if st.cached and not force:
            results.append(st.path)
            continue
        try:
            downloader(
                MODEL_REPO,
                st.spec.filename,
                revision=revision,
                local_dir=local_dir,
                force_download=force,
            )
        except LocalEntryNotFoundError as e:
            raise ModelDownloadError(
                "Could not reach huggingface.co. Connect to the internet and run "
                "`wowfish models pull`."
            ) from e
        except (RevisionNotFoundError, RepositoryNotFoundError, EntryNotFoundError) as e:
            raise ModelDownloadError(
                f"Model revision {revision} not found in {MODEL_REPO}. "
                "This is a packaging bug; please report it."
            ) from e
        except (HfHubHTTPError, OSError) as e:
            raise ModelDownloadError(f"Download of {st.spec.filename} failed: {e}") from e
        results.append(st.path)
    return results
