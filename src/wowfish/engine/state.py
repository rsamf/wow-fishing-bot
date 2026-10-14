from __future__ import annotations

from enum import Enum


class State(Enum):
    IDLE = "idle"
    CASTING = "casting"
    WAIT_BITE = "wait_bite"
    INTERACT = "interact"
    PAUSED = "paused"
    STOPPED = "stopped"
