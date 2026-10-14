from __future__ import annotations

import numpy as np

from wowfish.capture import WindowRef
from wowfish.errors import NotSupported


class StubCapturer:
    def open(self, window: WindowRef) -> None:
        raise NotSupported("screen capture")

    def grab(self, box=None) -> np.ndarray:
        raise NotSupported("screen capture")

    def close(self) -> None:
        return None
