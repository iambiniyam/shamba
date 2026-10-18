"""Evaluate the plant model on held-out PlantVillage images."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from PIL import Image

from shamba.model import PlantDiseaseModel

STOP = {"with", "and", "plant"}


def words(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]+", text.lower()) if word not in STOP}


def expected_text(folder: str) -> str:
    return folder.replace("___", " ").replace("_", " ").strip()


def match_label(folder: str, labels: list[str]) -> str:
    target = words(expected_text(folder))
    scored = []
    for label in labels:
        candidate = words(label)
        overlap = len(target & candidate) / len(target | candidate) if target | candidate else 0
        scored.append((overlap, label))
    return max(scored)[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/eval"))
    parser.add_argument("--out", type=Path, default=Path("docs/evaluation.json"))
    parser.add_argument("--model", type=Path, default=None)
    args = parser.parse_args()

    model = PlantDiseaseModel(model_path=args.model) if args.model else PlantDiseaseModel()
    labels = [info.raw for info in model.labels.values()]

    folders = sorted(path for path in args.data.iterdir() if path.is_dir())
    mapping = {}
    for folder in folders:
        mapping[folder.name] = match_label(folder.name, labels)

    rows = []
    started = time.perf_counter()
    for folder in folders:
        target = mapping[folder.name]
        images = sorted(folder.glob("*"))
        for image_path in images:
            image = Image.open(image_path)
            predictions = model.predict(image, top_k=3)
            predicted = [prediction.info.raw for prediction in predictions]
            rows.append(
                {
                    "file": str(image_path.relative_to(args.data)),
                    "expected": target,
                    "predicted": predicted[0],
                    "top3": predicted,
                    "top1": predicted[0] == target,
                    "top3_ok": target in predicted,
                    "confidence": round(predictions[0].confidence, 4),
                }
            )

    elapsed = time.perf_counter() - started
    top1 = sum(row["top1"] for row in rows) / len(rows)
    top3 = sum(row["top3_ok"] for row in rows) / len(rows)
    payload = {
        "images": len(rows),
        "classes": len(folders),
        "top1": round(top1, 4),
        "top3": round(top3, 4),
        "seconds": round(elapsed, 2),
        "ms_per_image": round(elapsed / len(rows) * 1000, 1),
        "mapping": mapping,
        "rows": rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2))
    print(json.dumps({key: payload[key] for key in ("images", "classes", "top1", "top3", "seconds", "ms_per_image")}, indent=2))


if __name__ == "__main__":
    main()
