import numpy as np
import onnxruntime as ort
import pytest

from wowfish import models

pytestmark = pytest.mark.integration


def test_pull_pinned_revision_and_run_each_model():
    paths = models.pull(models.MODEL_REVISION)
    assert len(paths) == len(models.MODELS)
    for p in paths:
        assert p.stat().st_size > 0
        sess = ort.InferenceSession(str(p), providers=["CPUExecutionProvider"])
        inp = sess.get_inputs()[0]
        shape = [d if isinstance(d, int) else 1 for d in inp.shape]
        (out,) = sess.run(None, {inp.name: np.zeros(shape, dtype=np.float32)})
        assert out is not None
    assert all(s.cached for s in models.status(models.MODEL_REVISION))
