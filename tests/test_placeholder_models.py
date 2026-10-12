import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from make_placeholder_models import build_identity_model


def test_identity_model_loads_and_passes_input_through():
    blob = build_identity_model("bobber")
    assert len(blob) < 1024
    sess = ort.InferenceSession(blob, providers=["CPUExecutionProvider"])
    x = np.random.rand(1, 3, 32, 32).astype(np.float32)
    (y,) = sess.run(None, {"input": x})
    assert np.array_equal(x, y)
