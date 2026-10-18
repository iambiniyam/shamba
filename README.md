# shamba

[![ci](https://github.com/iambiniyam/shamba/actions/workflows/ci.yml/badge.svg)](https://github.com/iambiniyam/shamba/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A plant health scanner that runs offline.

Take one clear photo of a leaf. shamba returns the three most likely crop diseases, a confidence score, and a treatment plan. It runs on a laptop, a Raspberry Pi, or a Jetson. After setup, no internet connection is needed.

![shamba web UI](docs/demo.png)

Status: early MVP. It works well on PlantVillage-style lab photos. Field photos are the next milestone.

## Why

Crop diseases cost farmers an estimated 30 to 40 percent of production each year. Home gardeners run into the same problems. Extension officers are spread thin, and a plant clinic visit can cost more than the plant is worth.

Most crop scanners send every photo to a paid API. shamba runs a small ONNX model on the device and pairs it with a local advice database. When the model is unsure, it says so and asks for a better photo.

## What it does

1. Diagnose: returns the top three crop and disease matches with confidence scores.
2. Explain: describes the disease and how it spreads.
3. Treat: starts with low-cost and organic options, and only mentions chemicals when they are likely needed.
4. Prevent: lists rotation, resistant varieties, sanitation, and watering practices.
5. Escalate: gives clear thresholds for calling a human extension officer.

## Quickstart

```bash
git clone https://github.com/iambiniyam/shamba.git
cd shamba
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python scripts/download_model.py
shamba diagnose tests/fixtures/maize_rust.jpg
shamba serve
```

The web UI is built for phones. Tap "Choose or take a photo" and the result appears as a treatment card.

If you need a smaller model, run `python scripts/download_model.py --variant mobilenet`. It downloads an 8.8 MB MobileNetV2 model. It is faster, but less accurate in our tests.

## Model

| Item | Value |
|---|---|
| Architecture | DINOv2-small with a linear classification head |
| Dataset | PlantVillage, 38 classes across 14 crops |
| Reported accuracy | 98.86% top-1 on a held-out PlantVillage split of 10,862 photos, according to the model card |
| Input | 224x224 RGB, 256 shortest-edge resize, ImageNet normalization |
| Size | 84 MB ONNX, fp32 |
| Runtime | onnxruntime on CPU by default |
| Latency | about 55 ms per image on an M-series Mac CPU |
| Lightweight option | MobileNetV2, 8.8 MB, via `--variant mobilenet` |

The model was trained on PlantVillage images. Those are lab-style photos of a single leaf on a plain background. It was not trained on field photos, so expect lower accuracy outdoors. The roadmap below covers that gap.

## How it works

```
photo
  |
  v
resize and center crop
  |
  v
ONNX DINOv2-small
  |
  v
top 3 predictions
  |
  v
advisory lookup
  |
  +--> CLI
  +--> web UI
```

- `src/shamba/model.py`: preprocessing and ONNX inference
- `src/shamba/labels.py`: parses both `Crop___Disease` and `Crop with Disease` class names
- `src/shamba/advice.py`: merges disease notes with general integrated pest management defaults
- `src/shamba/data/treatments.json`: 5 IPM defaults and 26 disease entries
- `src/shamba/server.py`: FastAPI app and the single-file mobile UI
- `scripts/download_model.py`: downloads the model from the Hugging Face mirror by default

## Tests

```bash
pytest -q
```

The suite has 13 tests covering labels, advice, preprocessing, inference, and the API. Model tests skip automatically if the weights are not downloaded.

## Accuracy and limits

This is decision support, not a plant doctor. It can be wrong, especially with:

- field photos that include soil, several leaves, or mixed symptoms
- crops outside the 38 PlantVillage classes
- nutrient deficiencies and herbicide damage, which can look like disease

Confirm the diagnosis before spending money on pesticide. Follow the product label and local registration rules. Low-confidence results are flagged and should be re-photographed.

Published numbers so far:

- Model card: 98.86% top-1 on a held-out PlantVillage split.
- Local fixtures: 4 out of 4 correct on maize rust, tomato late blight, potato early blight, and healthy tomato. See `tests/test_model.py`.
- Field trial: not done yet. The next step is 200 consented field photos from 3 regions, labelled by extension officers, plus a calibration report.

## Roadmap

The current label set covers maize, tomato, potato, pepper, apple, grape, cherry, peach, orange, strawberry, squash, soybean, raspberry, and blueberry. Next:

- cassava: mosaic disease, brown streak, green mite
- banana: Xanthomonas wilt, Panama disease
- sorghum and millet: downy mildew, striga
- common bean: anthracnose, bean fly
- a field-photo dataset collected with extension officers, with consent and geotags
- fine-tuning and INT8 quantization for a 2 MB mobile model
- an Android app with on-device inference and offline caching
- a Jetson and camera trap setup for community disease surveillance
- translated result cards

## Contributing

The most useful contribution is field photos with expert labels. Open an issue with the crop, region, and symptoms. For code changes, read `docs/architecture.md` first.

## License

Code is MIT. The default model is CC-BY-SA-4.0. The dataset and optional model have their own terms. See [THIRD_PARTY.md](THIRD_PARTY.md).
