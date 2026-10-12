# wow-fishing-forever

A vision-based fishing bot for **World of Warcraft: Forever**, successor to the 2019
[wow-fishing-bot](https://github.com/rsamf/wow-fishing-forever/tree/60d0710). It watches
the game window, finds the bobber with a small neural network, waits for the splash, and
reels in. No template images to capture, no screen regions to draw, no coordinates to set.

> **Use at your own risk.** Automating gameplay violates Blizzard's terms of service and can
> get your account banned. This project exists as a computer vision exercise. Nothing here
> hides from anti-cheat, and nothing here should be run on an account you care about.

## Status

**Alpha.** This release ships the installer, the `wowfish doctor` environment check, config
handling, and model download. Fishing itself lands in a later release once the detection
models are trained on Forever footage. Follow the releases page for progress.

## Install

### Players: download an executable

Grab the file for your OS from the
[latest release](https://github.com/rsamf/wow-fishing-forever/releases/latest):

| OS | file |
|---|---|
| Windows 10/11 (x86_64) | `wowfish-<version>-windows-x86_64.exe` |
| macOS (Apple Silicon) | `wowfish-<version>-macos-arm64` |
| Linux (x86_64) | `wowfish-<version>-linux-x86_64` |

The executables are not code-signed, so the first launch needs one extra step:

- **Windows:** SmartScreen shows "Windows protected your PC". Click *More info*, then
  *Run anyway*.
- **macOS:** Gatekeeper blocks it. Run `xattr -d com.apple.quarantine wowfish-*` in Terminal
  once, and `chmod +x wowfish-*` if needed. Intel Macs: use the developer install below.
- **Linux:** `chmod +x wowfish-*`.

Verify downloads against `SHA256SUMS.txt` from the same release.

### Developers: install from source

Requires [uv](https://docs.astral.sh/uv/).

    uv tool install git+https://github.com/rsamf/wow-fishing-forever@v1.0.0a1

or clone and run in place:

    git clone https://github.com/rsamf/wow-fishing-forever
    cd wow-fishing-forever
    uv sync --group dev
    uv run wowfish doctor

## First run

1. In WoW, open *Interface > Controls* and enable **Auto Loot**. The bot never looks for a
   loot window.
2. Put the Fishing ability on your action bar. Note its keybind (default `1` in wowfish).
3. Run `wowfish doctor`. Every line should be `ok` or `warn`; a `fail` means the install
   is broken and the line says why.
4. Run `wowfish models pull` to download the detection models from Hugging Face.
5. Run `wowfish config` to create the config file and see where it lives. Edit `cast_key`
   if your Fishing keybind is not `1`.

## Commands

| command | what it does |
|---|---|
| `wowfish doctor` | Check OS, display server, onnxruntime, models, config |
| `wowfish models pull` | Download model weights (pinned per release) |
| `wowfish models status` | Show which weights are cached and where |
| `wowfish config` | Create the config file if needed and print the resolved settings |
| `wowfish config --path` | Print only the config file location |
| `wowfish --version` | Print the version |

Add `--verbose` before any command for debug logging. `doctor` prints the log file path.

## How it works

The bot captures the game window, runs a tiny ONNX bobber localizer on each frame, crops
around the bobber, and runs a splash classifier on the crop. On a splash it right-clicks the
bobber after a short randomized delay, waits for Auto Loot, and casts again. Models are
trained in PyTorch on recorded Forever fishing sessions and exported to ONNX so the shipped
executable never needs torch. Weights live at
[huggingface.co/rsamf/wow-fishing-forever](https://huggingface.co/rsamf/wow-fishing-forever).

## Looking for the old bot?

The original OpenCV template-matching version is preserved at commit
[`60d0710`](https://github.com/rsamf/wow-fishing-forever/tree/60d0710). It targets WoW
Classic on Windows and requires manual setup. It is unmaintained.

## License

MIT. See [LICENSE](LICENSE).
