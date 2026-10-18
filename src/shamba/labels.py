"""Label parsing for PlantVillage-style and DINOv2-style class names."""

from __future__ import annotations

import re
from dataclasses import dataclass

RAW_LABELS: tuple[str, ...] = (
    "Apple Scab",
    "Apple with Black Rot",
    "Cedar Apple Rust",
    "Healthy Apple",
    "Healthy Blueberry Plant",
    "Cherry with Powdery Mildew",
    "Healthy Cherry Plant",
    "Corn (Maize) with Cercospora and Gray Leaf Spot",
    "Corn (Maize) with Common Rust",
    "Corn (Maize) with Northern Leaf Blight",
    "Healthy Corn (Maize) Plant",
    "Grape with Black Rot",
    "Grape with Esca (Black Measles)",
    "Grape with Isariopsis Leaf Spot",
    "Healthy Grape Plant",
    "Orange with Citrus Greening",
    "Peach with Bacterial Spot",
    "Healthy Peach Plant",
    "Bell Pepper with Bacterial Spot",
    "Healthy Bell Pepper Plant",
    "Potato with Early Blight",
    "Potato with Late Blight",
    "Healthy Potato Plant",
    "Healthy Raspberry Plant",
    "Healthy Soybean Plant",
    "Squash with Powdery Mildew",
    "Strawberry with Leaf Scorch",
    "Healthy Strawberry Plant",
    "Tomato with Bacterial Spot",
    "Tomato with Early Blight",
    "Tomato with Late Blight",
    "Tomato with Leaf Mold",
    "Tomato with Septoria Leaf Spot",
    "Tomato with Spider Mites or Two-spotted Spider Mite",
    "Tomato with Target Spot",
    "Tomato Yellow Leaf Curl Virus",
    "Tomato Mosaic Virus",
    "Healthy Tomato Plant",
)

_CROP_ALIASES = {
    "corn (maize)": "Maize",
    "corn": "Maize",
    "maize": "Maize",
    "pepper, bell": "Pepper",
    "bell pepper": "Pepper",
    "cherry (including sour)": "Cherry",
    "apple": "Apple",
    "blueberry": "Blueberry",
    "cherry": "Cherry",
    "grape": "Grape",
    "orange": "Orange",
    "peach": "Peach",
    "potato": "Potato",
    "raspberry": "Raspberry",
    "soybean": "Soybean",
    "squash": "Squash",
    "strawberry": "Strawberry",
    "tomato": "Tomato",
}

_DISEASE_ALIASES = {
    "apple scab": "Scab",
    "cercospora leaf spot gray leaf spot": "Cercospora and Gray Leaf Spot",
    "leaf blight (isariopsis leaf spot)": "Isariopsis Leaf Spot",
    "haunglongbing (citrus greening)": "Citrus Greening",
    "huanglongbing (citrus greening)": "Citrus Greening",
    "spider mites two-spotted spider mite": "Spider Mites or Two-spotted Spider Mite",
    "tomato yellow leaf curl virus": "Yellow Leaf Curl Virus",
    "tomato mosaic virus": "Mosaic Virus",
    "powdery mildew": "Powdery Mildew",
    "downy mildew": "Downy Mildew",
    "leaf mold": "Leaf Mold",
}

_SPECIAL = {
    "Apple Scab": ("Apple", "Scab"),
    "Cedar Apple Rust": ("Apple", "Cedar Apple Rust"),
    "Tomato Yellow Leaf Curl Virus": ("Tomato", "Yellow Leaf Curl Virus"),
    "Tomato Mosaic Virus": ("Tomato", "Mosaic Virus"),
}


def slug(text: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", text.lower())).strip("_")


@dataclass(frozen=True, slots=True)
class LabelInfo:
    raw: str
    crop: str
    disease: str
    healthy: bool

    @property
    def crop_slug(self) -> str:
        return slug(self.crop)

    @property
    def disease_slug(self) -> str:
        return slug(self.disease)

    @property
    def key(self) -> str:
        return f"{self.crop_slug}_{self.disease_slug}"


def _normalize_crop(raw: str) -> str:
    cleaned = raw.replace("_", " ").strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if cleaned in _CROP_ALIASES:
        return _CROP_ALIASES[cleaned]
    # Strip parenthetical qualifiers such as "Cherry (including sour)".
    base = re.sub(r"\s*\(.*?\)\s*", "", cleaned).strip()
    return _CROP_ALIASES.get(base, base.title())


def _normalize_disease(raw: str) -> str:
    cleaned = raw.replace("_", " ").strip(" _")
    cleaned = re.sub(r"\s+", " ", cleaned)
    key = cleaned.lower()
    if key in {"healthy", ""}:
        return "Healthy"
    if key in _DISEASE_ALIASES:
        return _DISEASE_ALIASES[key]
    # Title-case, preserving short words and parentheticals.
    words = []
    for word in cleaned.split():
        if word.lower() in {"and", "or", "of", "with"}:
            words.append(word.lower())
        elif word.isupper() and len(word) > 1:
            words.append(word)
        else:
            words.append(word[:1].upper() + word[1:].lower())
    return " ".join(words)


def _parse_plantvillage(raw: str) -> LabelInfo:
    """Handle `Crop___Disease` class names used by the DINOv2 model."""
    crop_part, disease_part = raw.split("___", 1)
    crop = _normalize_crop(crop_part)
    disease = _normalize_disease(disease_part)
    return LabelInfo(raw, crop, disease, disease == "Healthy")


def parse_label(raw: str) -> LabelInfo:
    raw = raw.strip()

    if "___" in raw:
        return _parse_plantvillage(raw)

    healthy = "healthy" in raw.lower()

    if raw in _SPECIAL:
        crop, disease = _SPECIAL[raw]
        return LabelInfo(raw, crop, disease, healthy)

    if healthy:
        plant = raw.lower().replace("healthy", "").replace("plant", "").strip()
        crop = _CROP_ALIASES.get(plant, plant.title())
        return LabelInfo(raw, crop, "Healthy", True)

    if " with " in raw:
        crop_part, disease = raw.split(" with ", 1)
        crop = _normalize_crop(crop_part)
        return LabelInfo(raw, crop, _normalize_disease(disease), False)

    raise ValueError(f"cannot parse label: {raw!r}")


def label_map() -> dict[int, LabelInfo]:
    return {index: parse_label(raw) for index, raw in enumerate(RAW_LABELS)}
