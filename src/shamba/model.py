"""ONNX inference for the PlantVillage MobileNetV2 classifier."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

from .config import Paths
from .labels import LabelInfo, parse_label

MEAN = np.array([0.5, 0.5, 0.5], dtype=np.float32)
STD = np.array([0.5, 0.5, 0.5], dtype=np.float32)
RESIZE = 256
CROP = 224


class ModelNotReady(RuntimeError):
    """Raised when the ONNX model is missing."""


@dataclass(frozen=True, slots=True)
class Prediction:
    info: LabelInfo
    confidence: float

    def as_dict(self) -> dict[str, object]:
        return {
            "label": self.info.raw,
            "crop": self.info.crop,
            "disease": self.info.disease,
            "healthy": self.info.healthy,
            "confidence": round(self.confidence, 4),
            "key": self.info.key,
        }


def preprocess(
    image: Image.Image,
    mean: np.ndarray = MEAN,
    std: np.ndarray = STD,
) -> np.ndarray:
    image = image.convert("RGB")
    width, height = image.size
    scale = RESIZE / min(width, height)
    resized = image.resize((max(1, round(width * scale)), max(1, round(height * scale))), Image.BICUBIC)
    left = (resized.width - CROP) // 2
    top = (resized.height - CROP) // 2
    cropped = resized.crop((left, top, left + CROP, top + CROP))

    array = np.asarray(cropped, dtype=np.float32) / 255.0
    array = (array - mean) / std
    return np.transpose(array, (2, 0, 1))[None, ...]


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max()
    exp = np.exp(shifted)
    return exp / exp.sum()


class PlantDiseaseModel:
    def __init__(self, model_path: Path | str | None = None, config_path: Path | str | None = None):
        defaults = Paths.default()
        self.model_path = Path(model_path) if model_path else defaults.model
        self.config_path = (
            Path(config_path)
            if config_path
            else self.model_path.parent / "config.json"
        )
        if not self.config_path.exists():
            self.config_path = defaults.config

        if not self.model_path.exists():
            raise ModelNotReady(
                f"model not found at {self.model_path}. Run: python scripts/download_model.py"
            )

        self.session = ort.InferenceSession(
            str(self.model_path), providers=["CPUExecutionProvider"]
        )
        self.input_name = self.session.get_inputs()[0].name

        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        raw_labels = {int(key): value for key, value in config["id2label"].items()}
        self.labels = {index: parse_label(raw) for index, raw in raw_labels.items()}

        preprocessor_path = self.model_path.parent / "preprocessor_config.json"
        if preprocessor_path.exists():
            preprocessor = json.loads(preprocessor_path.read_text(encoding="utf-8"))
            self.mean = np.array(preprocessor.get("image_mean", MEAN), dtype=np.float32)
            self.std = np.array(preprocessor.get("image_std", STD), dtype=np.float32)
        else:
            self.mean = MEAN
            self.std = STD

    def predict(self, image: Image.Image, top_k: int = 3) -> list[Prediction]:
        batch = preprocess(image, self.mean, self.std)
        logits = self.session.run(None, {self.input_name: batch})[0][0]
        probabilities = softmax(logits.astype(np.float32))
        best = np.argsort(probabilities)[::-1][:top_k]
        return [Prediction(self.labels[int(i)], float(probabilities[int(i)])) for i in best]
