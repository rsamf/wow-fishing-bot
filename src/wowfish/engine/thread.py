"""Run a FishingEngine on a background thread; the GUI and `run` consume its event queue."""

from __future__ import annotations

import threading
from typing import Any

from wowfish.engine import events as ev


class EngineThread:
    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self.error: BaseException | None = None
        self._thread = threading.Thread(target=self._run, name="wowfish-engine", daemon=True)

    @property
    def events(self) -> Any:
        return self.engine.events

    def start(self) -> None:
        self._thread.start()

    def is_alive(self) -> bool:
        return self._thread.is_alive()

    def stop(self, timeout: float = 2.0) -> None:
        self.engine.stop()
        self._thread.join(timeout)

    def _run(self) -> None:
        try:
            self.engine.run()
        except BaseException as e:  # the engine swallows its own errors; this is a last resort
            self.error = e
            self.engine.events.put(ev.Error(0.0, f"{type(e).__name__}: {e}"))
            self.engine.events.put(ev.Stopped(0.0, "error"))
