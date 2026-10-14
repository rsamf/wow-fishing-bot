"""Turns engine events into the words the console prints and the GUI shows."""

from __future__ import annotations

from wowfish.engine import events as ev


def describe(event: ev.Event) -> str:
    """One line per event; the console and the GUI say the same thing."""
    match event:
        case ev.StateChanged(did=did, next=nxt):
            return f"{did}. {nxt}."
        case ev.IconFound(score=score, where=(x, y)):
            return f"Found the bobber at ({x}, {y}), score {score:.2f}"
        case ev.IconLost():
            return "Lost sight of the bobber"
        case ev.BiteHeard(clip=clip, score=score):
            return f"Heard the splash ({score:.2f}, {clip})"
        case ev.KeyPressed(key=key, why="cast"):
            return f"Pressed {key} to cast"
        case ev.KeyPressed(key=key):
            return f"Pressed {key} to interact"
        case ev.Caught():
            return "Caught something; the bobber is gone"
        case ev.Timeout(what="icon", after_s=s):
            return f"No gear icon within {s:g} s; recasting"
        case ev.Timeout(what="bite", after_s=s):
            return f"No splash within {s:g} s; recasting"
        case ev.Timeout(after_s=s):
            return f"Bobber still there {s:g} s after Interact; recasting"
        case ev.Paused(reason=reason):
            return f"Paused: {reason}"
        case ev.Resumed():
            return "Resumed"
        case ev.Stats():
            return event.as_line()
        case ev.Error(message=message):
            return f"Error: {message}"
        case ev.Stopped(reason=reason):
            return f"Stopped ({reason})"
    return type(event).__name__
