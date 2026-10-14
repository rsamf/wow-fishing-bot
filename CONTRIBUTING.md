# Contributing

## Setup

Install [uv](https://docs.astral.sh/uv/) and optionally [just](https://github.com/casey/just).

    uv sync --group dev
    uv run pre-commit install   # optional: ruff on every commit

## Everyday commands

| just | without just |
|---|---|
| `just test` | `uv run pytest` |
| `just lint` | `uv run ruff check . && uv run ruff format --check .` |
| `just fmt` | `uv run ruff check --fix . && uv run ruff format .` |
| `just build` | `uv run pyinstaller --clean --noconfirm packaging/wowfish.spec` |
| `just smoke` | run the built executable: `--version`, `doctor`, `listen --list`, `calibrate` on the fixture |

Unit tests never touch the network, the display, or audio hardware: `soundcard`, `mss`, and
`Xlib` are imported lazily and the tests stub them. The X11 capture tests run only when
`DISPLAY` is set. Set `WOWFISH_HOME` to redirect config, cache, and logs; the test suite does
this automatically.

## Layout

    src/wowfish/
      cli.py        typer app; registers the commands below
      commands/     calibrate, watch, listen, verify-bite (one module each)
      config.py     TOML config: [game], [vision], [audio]; defaults, validation, save
      paths.py      config / cache / log locations (WOWFISH_HOME override)
      doctor.py     environment probes
      assets/       interact-icon sprites (PNG) and splash clips (WAV) shipped in the package
      vision/       templates, regions, masked matcher, acquire/track search, calibration, annotate
      audio/        WAV I/O, log-mel features, fingerprints, bite detector, loopback devices
      capture/      window lookup and capture: X11 (ctypes XGetImage), mss, stub
      input/        keyboard/mouse protocol (+ stub; real devices arrive with the runtime)
    scripts/        release preflight, clip conversion (ffmpeg, dev only)
    packaging/      PyInstaller spec
    tests/          unit tests, synthetic frame/audio helpers, tests/fixtures/

## Branches and releases

- `forever` is the development branch for the rewrite. `main` holds the legacy bot until
  the rewrite fishes end to end.
- Versions are PEP 440 (`1.0.0a1`, `1.0.0b1`, `1.0.0rc1`, `1.0.0`). Tags are `v` + version.
- To cut a release: bump `version` in `pyproject.toml`, commit, then
  `git tag v<version> && git push origin v<version>`. The release workflow verifies the tag
  matches the version and that the package assets are present, builds three executables,
  and publishes a GitHub Release (marked prerelease for a/b/rc versions).

## Updating the bundled clips or sprites

The splash clips are converted once from the game's Vorbis files with
`uv run python scripts/convert_clips.py <dir-with-ogg-files>` (needs `ffmpeg`) and committed
as 16-bit mono 22050 Hz WAV. The gear sprites are cropped from the client's 2x crosshair
sheet. Neither step runs at install or build time.

## Pull requests

CI runs lint, unit tests, and a PyInstaller smoke build on Linux, Windows, and macOS. Keep
PRs green on all three. Add tests for behavior changes.
