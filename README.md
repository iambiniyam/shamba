# shamba

**Plant health scanner for gardeners and farmers — offline, on any laptop or edge device.**

One clear photo of a leaf → a likely diagnosis, a confidence score, and a treatment plan you can afford. Runs on a laptop, a Raspberry Pi, or a Jetson — no internet after setup.

```
$ shamba diagnose maize_leaf.jpg

┏━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Rank ┃ Crop  ┃ Disease     ┃ Confidence ┃
┡━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ 1    │ Maize │ Common Rust │ 100.0%     │
│ 2    │ Maize │ Northern... │ 0.0%       │
└──────┴───────┴─────────────┴────────────┘
```

> **Status:** early MVP. Strong on PlantVillage-style lab photos, not yet validated on field photos. See [Evaluation](#evaluation).

![shamba web UI](docs/demo.png)

## Why

- Pests and diseases destroy **30–40%** of crop production worldwide, and home gardeners lose plants to the same problems.
- Extension services are stretched thin, and a plant clinic visit costs more than most gardeners will spend.
- Most AI crop tools assume fast internet, a modern phone, and a paid API.

`shamba` runs a **38-class classifier** (DINOv2-small, 84 MB ONNX, CPU) and pairs it with an integrated pest-management knowledge base. It is small enough for cheap hardware and honest enough to say *"I'm not sure."*

## What it does

1. **Diagnose** — top-3 crop/disease predictions with softmax confidence.
2. **Explain** — what the disease is, why it spreads, what to do now.
3. **Treat** — low-cost/organic options first, chemicals only when needed, no invented doses.
4. **Prevent** — rotation, resistant varieties, sanitation, water management.
5. **Escalate** — clear thresholds for calling a human extension officer.

## Quickstart

```bash
git clone https://github.com/iambiniyam/shamba.git
cd shamba
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python scripts/download_model.py        # ~84 MB, uses the HF mirror by default
shamba diagnose tests/fixtures/maize_rust.jpg
shamba serve                            # http://127.0.0.1:8787
```

The web UI is mobile-first: tap **Choose or take a photo**, and the result renders as a treatment card.

**Low-bandwidth / low-power option:** `python scripts/download_model.py --variant mobilenet` downloads the 8.8 MB MobileNetV2 model instead. It is faster and smaller, but noticeably less accurate in our tests.

## Model

| Item | Value |
|---|---|
| Architecture | DINOv2-small + linear classification head |
| Dataset | PlantVillage, 38 classes across 14 crops |
| Reported accuracy | **98.86%** top-1 on a held-out PlantVillage split (10,862 photos, per model card) |
| Input | 224×224 RGB, 256 shortest-edge resize, ImageNet normalization |
| Size | 84 MB ONNX (fp32) |
| Runtime | `onnxruntime`, CPU by default |
| Latency | ~55 ms/image on an M-series Mac CPU |
| Lightweight option | MobileNetV2, 8.8 MB (`--variant mobilenet`) |

The model is **not trained on African field photos**. PlantVillage images are lab-style, single-leaf, uniform backgrounds. Field accuracy will be lower. Closing that gap is the point of the roadmap, not something to hide.

## Architecture

```
photo ─► resize/crop ─► ONNX DINOv2-small ─► top-k ─► advice KB ─► CLI / web UI
                                                      │
                                                      └─ confidence gate (<60% → retake photo)
```

- `src/shamba/model.py` — preprocessing + ONNX inference
- `src/shamba/labels.py` — 38 raw labels → crop/disease/stable key (both `Crop___Disease` and `Crop with Disease`)
- `src/shamba/advice.py` — merges disease-specific notes with IPM defaults
- `src/shamba/data/treatments.json` — 5 IPM defaults + 26 disease entries
- `src/shamba/server.py` — FastAPI + single-file mobile UI
- `scripts/download_model.py` — model fetch (HF mirror or huggingface.co)
- `docs/architecture.md` — contracts, deployment, evaluation plan

## Tests

```bash
pytest -q     # 13 tests: labels, advice, preprocessing, model, API
```

Model tests skip automatically if weights are not downloaded.

## Safety

This is **decision support, not a plant doctor**. It can be wrong, especially on:
- field photos with mixed symptoms, soil, or multiple leaves;
- crops outside the 38 PlantVillage classes;
- nutrient deficiencies and herbicide damage that mimic disease.

Always confirm before spending money on pesticide, and follow the product label and national registration rules. Low-confidence predictions are explicitly flagged and should be re-photographed.

## Roadmap

The current label set covers maize, tomato, potato, pepper, apple, grape, cherry, peach, orange, strawberry, squash, soybean, raspberry, and blueberry. Next:

- [ ] Cassava: mosaic disease, brown streak, green mite
- [ ] Banana: Xanthomonas wilt, Panama disease
- [ ] Sorghum and millet: downy mildew, striga
- [ ] Common bean: anthracnose, bean fly
- [ ] Field-photo dataset collected with extension officers (consented, geotagged)
- [ ] Fine-tune + INT8 quantization for a ~2 MB mobile model
- [ ] Android app with on-device inference and offline caching
- [ ] Jetson + camera trap for community disease surveillance
- [ ] More languages for result cards (text, not speech)

## Evaluation

Published numbers so far:

- **Model card:** 98.86% top-1 on a held-out PlantVillage split.
- **Our fixtures:** 4/4 correct on maize rust, tomato late blight, potato early blight, and healthy tomato (see `tests/test_model.py`).
- **Not done yet:** a field trial. The next step is 200 consented field photos from 3 regions, labelled by extension officers, plus a calibration report (does 60% confidence mean 60% accuracy?).

## Contributing

The highest-value contribution is **field photos with expert labels**. Open an issue with the crop, region, and symptoms. Code contributions: see `docs/architecture.md`.

## License

Code is MIT. The default model is CC-BY-SA-4.0; the dataset and optional model carry their own terms. See [THIRD_PARTY.md](THIRD_PARTY.md).
