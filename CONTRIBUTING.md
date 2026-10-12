# Contributing

## Setup

Install [uv](https://docs.astral.sh/uv/) and optionally [just](https://github.com/casey/just).

    uv sync --group dev
    uv run pre-commit install   # optional: ruff on every commit

## Everyday commands

| just | without just |
|---|---|
| `just test` | `uv run pytest` |
| `just test-integration` | `uv run pytest -m integration` (hits huggingface.co) |
| `just lint` | `uv run ruff check . && uv run ruff format --check .` |
| `just fmt` | `uv run ruff check --fix . && uv run ruff format .` |
| `just build` | `uv run pyinstaller --clean --noconfirm packaging/wowfish.spec` |
| `just smoke` | `./dist/wowfish --version && ./dist/wowfish doctor` |

Unit tests never touch the network or the display. Set `WOWFISH_HOME` to redirect config,
cache, and logs; the test suite does this automatically.

## Layout

    src/wowfish/
      cli.py       typer commands
      config.py    TOML config, defaults, warnings, errors
      paths.py     config / cache / log locations (WOWFISH_HOME override)
      models.py    model manifest, pinned Hub revision, download
      doctor.py    environment probes
      capture/     screen capture protocol (+ stub)
      input/       keyboard/mouse protocol (+ stub)
    scripts/       release preflight, placeholder model builder, Hub publisher
    packaging/     PyInstaller spec
    tests/         unit tests; tests/integration/ needs network

## Branches and releases

- `forever` is the development branch for the rewrite. `main` holds the legacy bot until
  the rewrite fishes end to end.
- Versions are PEP 440 (`1.0.0a1`, `1.0.0b1`, `1.0.0rc1`, `1.0.0`). Tags are `v` + version.
- To cut a release: bump `version` in `pyproject.toml`, commit, then
  `git tag v<version> && git push origin v<version>`. The release workflow verifies the tag
  matches the version and that the pinned model revision exists on the Hub, builds three
  executables, and publishes a GitHub Release (marked prerelease for a/b/rc versions).

## Updating model weights

1. `uv run python scripts/publish_models.py <dir-with-onnx-files> "message"` prints a commit hash.
2. Paste it into `MODEL_REVISION` in `src/wowfish/models.py`.
3. `uv run pytest -m integration` to confirm the download path still works.

## Pull requests

CI runs lint, unit tests, integration tests, and a PyInstaller smoke build on Linux,
Windows, and macOS. Keep PRs green on all three. Add tests for behavior changes.
