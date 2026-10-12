"""Create (if needed) the public Hub model repo and upload a folder as one commit.

Usage: uv run python scripts/publish_models.py MODEL_DIR "commit message"
Prints the resulting commit hash. Paste it into MODEL_REVISION in src/wowfish/models.py.
Requires `hf auth login` as the repo owner.
"""

from __future__ import annotations

import sys
from pathlib import Path

from huggingface_hub import HfApi

from wowfish.models import MODEL_REPO

README = """---
license: mit
tags: [onnx, world-of-warcraft, fishing]
---
# wow-fishing-forever models

ONNX weights used by [wowfish](https://github.com/rsamf/wow-fishing-forever).
Each wowfish release pins one commit of this repo.

| file | role |
|---|---|
| bobber.onnx | locate the fishing bobber in a frame |
| splash.onnx | classify whether the bobber crop shows a splash |

Current files are identity placeholders so the download path can be tested end to end.
"""


def main(model_dir: Path, message: str) -> None:
    api = HfApi()
    api.create_repo(MODEL_REPO, repo_type="model", exist_ok=True, private=False)
    (model_dir / "README.md").write_text(README)
    info = api.upload_folder(
        repo_id=MODEL_REPO, repo_type="model", folder_path=str(model_dir), commit_message=message
    )
    print(info.oid)


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2])
