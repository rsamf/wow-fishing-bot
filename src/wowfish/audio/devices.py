"""Enumerate and open system loopback devices. `soundcard` is imported lazily: CI has no audio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from wowfish.audio import AudioUnavailable
from wowfish.audio._soundcard import SoundcardSource


@dataclass(frozen=True)
class LoopbackDevice:
    id: str
    name: str
    is_default: bool


def _soundcard() -> Any:
    try:
        import soundcard
    except Exception as e:  # ImportError, or the Pulse/CoreAudio client failing at import
        raise AudioUnavailable(f"soundcard backend unavailable: {type(e).__name__}: {e}") from e
    return soundcard


def _loopback_mics() -> tuple[list[Any], Any]:
    sc = _soundcard()
    try:
        mics = sc.all_microphones(include_loopback=True)
        mics = [m for m in mics if getattr(m, "isloopback", False)]
    except Exception as e:
        raise AudioUnavailable(f"cannot list audio devices: {type(e).__name__}: {e}") from e
    try:
        speaker = sc.default_speaker()
    except Exception:
        speaker = None
    return mics, speaker


def _is_default(mic: Any, speaker: Any) -> bool:
    if speaker is None:
        return False
    return str(speaker.id) in str(mic.id) or str(speaker.name) in str(mic.name)


def list_loopback_devices() -> list[LoopbackDevice]:
    mics, speaker = _loopback_mics()
    return [LoopbackDevice(str(m.id), str(m.name), _is_default(m, speaker)) for m in mics]


def open_loopback(
    selector: str = "", *, sample_rate: int = 22050, blocksize: int = 1024
) -> SoundcardSource:
    """Open by exact id, id substring, or case-insensitive name substring.

    An empty selector opens the monitor of the default output.
    """
    mics, speaker = _loopback_mics()
    if not mics:
        raise AudioUnavailable(
            "no loopback devices found (macOS needs a virtual device such as BlackHole)"
        )
    if selector:
        wanted = selector.lower()
        mic = next(
            (
                m
                for m in mics
                if selector == str(m.id) or selector in str(m.id) or wanted in str(m.name).lower()
            ),
            None,
        )
        if mic is None:
            raise AudioUnavailable(
                f"no loopback device matches {selector!r}; run `wowfish listen --list`"
            )
    else:
        mic = next((m for m in mics if _is_default(m, speaker)), mics[0])
    return SoundcardSource(mic, sample_rate, blocksize)
