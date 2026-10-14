import queue
import threading
import time

from wowfish.engine import events as ev
from wowfish.engine.thread import EngineThread


class _FakeEngine:
    def __init__(self, fail=False):
        self.events = queue.Queue()
        self.stopped = threading.Event()
        self.fail = fail
        self.stats = ev.Stats(0.0)

    def run(self):
        if self.fail:
            raise RuntimeError("device vanished")
        while not self.stopped.is_set():
            time.sleep(0.01)
        self.events.put(ev.Stopped(1.0, "user"))

    def stop(self):
        self.stopped.set()


def test_thread_runs_the_engine_and_stop_joins():
    eng = _FakeEngine()
    t = EngineThread(eng)
    t.start()
    assert t.is_alive()
    t.stop(timeout=2.0)
    assert not t.is_alive()
    assert isinstance(eng.events.get_nowait(), ev.Stopped)


def test_an_exception_in_run_becomes_error_and_stopped_events():
    eng = _FakeEngine(fail=True)
    t = EngineThread(eng)
    t.start()
    t.stop(timeout=2.0)
    kinds = []
    while not eng.events.empty():
        kinds.append(eng.events.get_nowait())
    assert isinstance(kinds[0], ev.Error) and "device vanished" in kinds[0].message
    assert isinstance(kinds[1], ev.Stopped) and kinds[1].reason == "error"
