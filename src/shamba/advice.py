"""Treatment advice: merge general IPM guidance with disease-specific notes."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any

from .model import Prediction

DISCLAIMER = (
    "General guidance, not a substitute for a local extension officer or the pesticide label. "
    "Confirm the diagnosis locally and follow national registration rules before spraying."
)


def load_treatments() -> dict[str, Any]:
    raw = files("shamba.data").joinpath("treatments.json").read_text(encoding="utf-8")
    return json.loads(raw)


def infer_type(disease: str) -> str:
    text = disease.lower()
    if any(word in text for word in ("virus", "curl", "mosaic")):
        return "viral"
    if any(word in text for word in ("bacteria", "greening", "bacterial")):
        return "bacterial"
    if any(word in text for word in ("mite", "spider", "pest", "insect")):
        return "pest"
    return "fungal"


def get_advice(prediction: Prediction) -> dict[str, Any]:
    data = load_treatments()
    info = prediction.info

    if info.healthy:
        advice = dict(data["defaults"]["healthy"])
    else:
        specific = data["diseases"].get(info.key)
        kind = (specific or {}).get("type") or infer_type(info.disease)
        advice = {**data["defaults"][kind], **(specific or {})}

    advice["crop"] = info.crop
    advice["disease"] = info.disease
    advice["healthy"] = info.healthy
    advice["confidence"] = round(prediction.confidence, 4)
    advice["disclaimer"] = DISCLAIMER

    if prediction.confidence < 0.60:
        advice["confidence_note"] = (
            "Low confidence. Take another photo in daylight, fill the frame with one leaf, "
            "and include both healthy and affected areas. Ask again before acting."
        )
    return advice
