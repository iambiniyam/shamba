"""Paths and defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_DIR = PACKAGE_DIR.parents[1]


def model_dir() -> Path:
    return Path(
        os.getenv("SHAMBA_MODEL_DIR", str(Path.home() / ".shamba" / "models" / "plant-disease"))
    )


@dataclass(slots=True)
class Paths:
    model: Path
    config: Path

    @classmethod
    def default(cls) -> Paths:
        base = model_dir()
        return cls(model=base / "model.onnx", config=base / "config.json")


DEFAULT_MODEL_BASE = (
    "https://hf-mirror.com/onnx-community/"
    "mobilenet_v2_1.0_224-plant-disease-identification-ONNX/resolve/main"
)
