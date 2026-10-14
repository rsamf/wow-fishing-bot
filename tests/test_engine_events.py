import numpy as np

from wowfish.engine.events import (
    BiteHeard,
    Calibrated,
    Caught,
    Error,
    IconFound,
    IconLost,
    KeyPressed,
    Paused,
    Resumed,
    StateChanged,
    Stats,
    Stopped,
    Timeout,
)
from wowfish.engine.state import State
from wowfish.gui.presenter import describe


def test_states_exist_in_order():
    assert [s.name for s in State] == [
        "IDLE",
        "CASTING",
        "WAIT_BITE",
        "INTERACT",
        "PAUSED",
        "STOPPED",
    ]


def test_state_changed_joins_did_and_next():
    ev = StateChanged(1.0, State.CASTING, "Pressed 8 to cast", "Looking for the gear icon")
    assert describe(ev) == "Pressed 8 to cast. Looking for the gear icon."


def test_icon_found_names_the_place_and_score():
    thumb = np.zeros((270, 480, 3), dtype=np.uint8)
    ev = IconFound(2.0, thumb, (10, 20, 6, 6), 0.912, 58, (2622, 899))
    assert describe(ev) == "Found the bobber at (2622, 899), score 0.91"


def test_other_event_words():
    assert describe(IconLost(3.0)) == "Lost sight of the bobber"
    assert describe(BiteHeard(4.0, "fishingbobber_2", 0.843)) == (
        "Heard the splash (0.84, fishingbobber_2)"
    )
    assert describe(KeyPressed(5.0, "8", "cast")) == "Pressed 8 to cast"
    assert describe(KeyPressed(5.0, "f", "bite")) == "Pressed f to interact"
    assert describe(Caught(6.0)) == "Caught something; the bobber is gone"
    assert describe(Timeout(7.0, "icon", 6.0)) == "No gear icon within 6 s; recasting"
    assert describe(Timeout(7.0, "bite", 30.0)) == "No splash within 30 s; recasting"
    assert describe(Timeout(7.0, "loot", 3.0)) == "Bobber still there 3 s after Interact; recasting"
    assert describe(Paused(8.0, "World of Warcraft is not the focused window")) == (
        "Paused: World of Warcraft is not the focused window"
    )
    assert describe(Resumed(9.0, State.WAIT_BITE)) == "Resumed"
    assert describe(Calibrated(9.5, 58, 0.92)) == "Measured the gear icon at 58 px (score 0.92)"
    assert describe(Error(10.0, "boom")) == "Error: boom"
    assert describe(Stopped(11.0, "session limit")) == "Stopped (session limit)"


def test_stats_line_and_counts():
    s = Stats(12.0, casts=3, catches=2, misses=1, bites_heard=2, elapsed_s=252.0)
    assert s.as_line() == "casts 3, catches 2, misses 1, bites 2, 04:12"
    assert describe(s) == s.as_line()
    assert Stats(0.0).as_line() == "casts 0, catches 0, misses 0, bites 0, 00:00"
