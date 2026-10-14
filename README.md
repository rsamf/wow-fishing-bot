# wow-fishing-forever

A fishing bot for **World of Warcraft: Forever**, successor to the 2019
[wow-fishing-bot](https://github.com/rsamf/wow-fishing-forever/tree/60d0710). It watches the
game window for the built-in interact icon over your bobber, listens to the game's own splash
sound for the bite, and presses your Interact key. No template images to capture, no screen
regions to draw, no coordinates to set.

> **Use at your own risk.** Automating gameplay violates Blizzard's terms of service and can
> get your account banned. This project exists as a computer vision exercise. Nothing here
> hides from anti-cheat, and nothing here should be run on an account you care about.

## Status

**Alpha.** This release ships the detection core: icon calibration, the live watcher, the
audio bite detector, and the environment check. The fishing loop and the desktop GUI land in
the next releases. Follow the releases page for progress.

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

In the game:

1. *Options > Gameplay > Controls*: enable **Auto Loot**.
2. *Options > Keybindings > Targeting*: bind **Interact With Target**. wowfish assumes `f`.
3. Put **Fishing** on an action bar key. wowfish assumes `1`.
4. Type `/console SoftTargetIconGameObject 1` once. This shows the gold gear icon over your
   bobber whenever it is close enough to interact with.
5. *Options > Sound*: set **Ambience** and **Music** to 0 and keep **Sound Effects** up. The
   bite is a sound effect; ocean ambience is the same kind of noise and buries it.

On your machine:

- **Linux (GNOME on Wayland):** the first synthetic key press opens a "Remote Desktop" dialog.
  Switch on *Allow Remote Interaction* and click *Share*. Until you do, key presses are
  silently dropped.
- **macOS:** install a virtual loopback device such as
  [BlackHole](https://existential.audio/blackhole/) and route the game's audio through it.
  macOS has no built-in way to record what it plays.
- **Windows:** nothing to do. Game audio is captured through WASAPI loopback.

Then open the window and work down its Setup tab:

    wowfish gui          # or double-click wowfish-gui

It saves your keys, picks the audio device (with a live level so you can see the game is
heard), grabs the game window to measure the gear icon, and records a minute of your own
fishing to check the splash. The Fish tab's Start button lists anything still missing.

The same steps from the terminal:

    wowfish doctor
    wowfish config                      # creates the config file; edit cast_key / interact_key
    wowfish listen --record bite.wav --seconds 60   # fish one bite by hand while it records
    wowfish verify-bite bite.wav --save
    wowfish run                         # measures the icon on its first cast; Ctrl-C stops

## Running the bot

Stand at the water with the game window focused and press Start (GUI) or run `wowfish run`.
The first cast of every run measures the gear icon's on-screen size, because resolution and UI
scale change it; a saved calibration only makes that first cast faster. If two casts in a row
never show the icon, the next cast measures it again, so a changed resolution mid-session heals
itself. Each cast: press the cast key, look for the gear icon for 6 s, listen for the splash for up to
30 s, press Interact, wait up to 3 s for the bobber to disappear (Auto Loot takes the catch),
pause a random half-second to two seconds, cast again. If the gear icon never shows or no
splash comes, it recasts and counts a miss. If another window takes focus it pauses rather
than typing into that window, and resumes when the game is focused again. The session ends
after `session_minutes` (default 60) or when you stop it.

Every step is reported as "what I did. What I will do next.", for example "Found the bobber
at (2622, 899). Waiting for a splash; will press f when I hear one." The GUI also shows the
frame the icon was found in with a box around it. Timeouts and pauses are in the `[run]`
table of the config file.

## Commands

| command | what it does |
|---|---|
| `wowfish gui` | The setup and fishing window |
| `wowfish run [--minutes N]` | Fish from the terminal until Ctrl-C or the session limit |
| `wowfish doctor` | Check OS, display, OpenCV, audio devices, game window, input, calibration, config |
| `wowfish calibrate SHOT.png [--save]` | Measure the interact icon's on-screen size from a screenshot |
| `wowfish watch --live` | Show what the matcher sees: phase, score, position, milliseconds per frame |
| `wowfish watch --from DIR` | Same, over saved frames; `--save-frames` writes annotated thumbnails |
| `wowfish listen [--list] [--record WAV]` | List loopback devices, meter game audio, print bites as they are heard |
| `wowfish verify-bite WAV [--save]` | Score a recording against every splash clip and pick the bite |
| `wowfish config` | Create the config file if needed and print the resolved settings |
| `wowfish config --path` | Print only the config file location |
| `wowfish --version` | Print the version |

Add `--verbose` before any command for debug logging. `doctor` prints the log file path.

## How it works

**The icon.** The client draws a gold gear sprite over the bobber when it is in interact
range. wowfish ships that sprite at its five native sizes and matches it against the game
window with a masked, mean-subtracted template match, so only the gear's own pixels count and
water never out-scores it. Calibration measures the on-screen size once and only accepts a
candidate whose score drops sharply at neighbouring sizes, which a real gear does and a patch
of skin or UI gold does not. After each cast the whole frame is searched; once the icon is
found only a small box around it is tracked.

**The bite.** The client plays one of its splash clips when a fish bites. wowfish ships those
clips and fingerprints the first 0.8 seconds of each as a log-mel spectrogram with the gain
removed. Game audio is captured from the system loopback device and correlated against the
fingerprints every 3 milliseconds; a correlation above your threshold is the bite. Silence is
ignored outright, and the loudest other game sounds score about 0.63 against bites of 0.72 to 0.94.
`verify-bite` sets that threshold from a recording of your own setup.

**What it never does.** No memory reading, no injected code, no addon, no network traffic.
It looks at pixels and listens to sound, then presses the keys you told it about.

## Looking for the old bot?

The original OpenCV template-matching version is preserved at commit
[`60d0710`](https://github.com/rsamf/wow-fishing-forever/tree/60d0710). It targets WoW
Classic on Windows and requires manual setup. It is unmaintained.

## License

MIT. See [LICENSE](LICENSE).
