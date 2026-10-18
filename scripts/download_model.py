#!/usr/bin/env python3
"""Download a shamba crop-disease classifier.

Defaults to the DINOv2-small model (84 MB, ~98.9% PlantVillage held-out).
Use --variant mobilenet for the 8.8 MB CPU-friendly model.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
from pathlib import Path

from shamba.config import Paths

VARIANTS = {
    "dinov2": {
        "base": "https://hf-mirror.com/rodynaemad/plant-disease-dinov2-small/resolve/main",
        "files": {
            "config.json": "config.json",
            "preprocessor_config.json": "preprocessor_config.json",
            "onnx/model_with_features.onnx": "model.onnx",
        },
        "size": "~84 MB",
    },
    "mobilenet": {
        "base": (
            "https://hf-mirror.com/onnx-community/"
            "mobilenet_v2_1.0_224-plant-disease-identification-ONNX/resolve/main"
        ),
        "files": {
            "config.json": "config.json",
            "preprocessor_config.json": "preprocessor_config.json",
            "onnx/model.onnx": "model.onnx",
        },
        "size": "~9 MB",
    },
}


def fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url, timeout=180) as response, tmp.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    tmp.replace(dest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=sorted(VARIANTS), default="dinov2")
    parser.add_argument("--base-url", default=None, help="Override the model host.")
    parser.add_argument("--dest", type=Path, default=Paths.default().model.parent)
    args = parser.parse_args()

    variant = VARIANTS[args.variant]
    base = (args.base_url or variant["base"]).rstrip("/")
    print(f"shamba model: {args.variant} ({variant['size']}) → {args.dest}")

    for remote, local in variant["files"].items():
        url = f"{base}/{remote}"
        dest = args.dest / local
        print(f"→ {url}")
        try:
            fetch(url, dest)
        except Exception as exc:  # noqa: BLE001 - CLI should report, not traceback
            print(f"failed: {exc}", file=sys.stderr)
            return 1
        print(f"  saved {dest} ({dest.stat().st_size / 1e6:.1f} MB)")

    print("done. try: shamba diagnose tests/fixtures/maize_rust.jpg")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
