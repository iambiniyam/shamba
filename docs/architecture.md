# Architecture

```
                    ┌─────────────────────────────┐
  leaf photo ──────►│ preprocess (256 → 224 crop) │
                    └──────────────┬──────────────┘
                                   ▼
                    ┌─────────────────────────────┐
                    │ ONNX DINOv2-small + head    │  CPU, ~55 ms (M-series)
                    └──────────────┬──────────────┘
                                   ▼
                    ┌─────────────────────────────┐
                    │ 38 logits → softmax → top-k │
                    └──────────────┬──────────────┘
                                   ▼
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
   ┌─────────────────────┐                   ┌─────────────────────┐
   │ advice.py           │                   │ confidence gate     │
   │ defaults by type +  │                   │ <60% → retake photo │
   │ disease-specific    │                   └─────────────────────┘
   └──────────┬──────────┘
              ▼
   CLI (rich) / FastAPI UI / JSON API
```

## Modules

| Module | Responsibility |
|---|---|
| `labels.py` | Parse both `Corn with Common Rust` and `Corn_(maize)___Common_rust_` into `{crop, disease, key}`. |
| `model.py` | ONNX session, preprocessing, softmax, top-k. |
| `advice.py` | Merge type-level IPM defaults with disease-specific notes; add confidence and disclaimer. |
| `data/treatments.json` | 5 IPM defaults + 26 disease entries. |
| `server.py` | Mobile-first upload UI and `/api/diagnose`. |
| `cli.py` | `diagnose`, `serve`, `doctor`. |

## Label contract

Every model label must normalize to a stable key: `{crop_slug}_{disease_slug}`.
That key is the join between the model and `treatments.json`.

Examples:

```
Corn_(maize)___Common_rust_  → maize_common_rust
Tomato___Late_blight         → tomato_late_blight
Pepper,_bell___Bacterial_spot → pepper_bacterial_spot
Apple___healthy              → apple_healthy
```

## Adding a crop or disease

1. Add the class name to the model's `config.json` (or fine-tune and export).
2. Confirm `parse_label()` produces a sensible key — add an alias if not.
3. Add an entry under `diseases` in `treatments.json`, or let it fall back to
   the type defaults (fungal / bacterial / viral / pest / healthy).
4. Add a fixture image and a test asserting the crop.

## Deployment

- **Laptop / clinic PC:** `shamba serve`, CPU is enough.
- **Jetson Orin Nano:** ONNX Runtime CPU works; optionally install the TensorRT
  execution provider and export a 224×224 engine for lower latency.
- **Android:** export the same ONNX graph to ONNX Runtime Mobile or TFLite;
  the preprocessing contract stays identical.
- **Raspberry Pi:** use `--variant mobilenet` (8.8 MB) and accept lower accuracy.

## Evaluation plan

- PlantVillage held-out split: top-1, top-3, per-class recall.
- Field set: 200 consented photos from 3 regions, labelled by extension officers.
- Calibration: bucket predictions by confidence and compare empirical accuracy.
- Failure analysis: nutrient deficiency, herbicide damage, mixed infections.
