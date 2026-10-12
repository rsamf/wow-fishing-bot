"""Build tiny valid ONNX graphs that stand in for the real models until training ships.

Usage: uv run python scripts/make_placeholder_models.py OUT_DIR
"""

from __future__ import annotations

import sys
from pathlib import Path

import onnx
from onnx import TensorProto, helper

SHAPE = [1, 3, 32, 32]


def build_identity_model(name: str) -> bytes:
    inp = helper.make_tensor_value_info("input", TensorProto.FLOAT, SHAPE)
    out = helper.make_tensor_value_info("output", TensorProto.FLOAT, SHAPE)
    node = helper.make_node("Identity", ["input"], ["output"])
    graph = helper.make_graph([node], f"{name}_placeholder", [inp], [out])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    model.ir_version = 8
    model.doc_string = f"Placeholder {name} model. Identity. Replaced by sub-project 2."
    onnx.checker.check_model(model)
    return model.SerializeToString()


def main(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for role in ("bobber", "splash"):
        path = out_dir / f"{role}.onnx"
        path.write_bytes(build_identity_model(role))
        print(f"wrote {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
