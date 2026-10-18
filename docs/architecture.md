# Architecture

```
leaf photo
    |
    v
preprocess: resize shortest edge to 256, center crop to 224
    |
    v
ONNX DINOv2-small with a linear head (CPU, about 55 ms on an M-series Mac)
    |
    v
38 logits -> softmax -> top 3
    |
    +--> advice.py: type defaults plus disease notes
    |
    +--> confidence gate: below 60%, ask for another photo
    |
    v
CLI, FastAPI UI, or JSON API
```

## Modules

| Module | Responsibility |
|---|---|
| `labels.py` | Parse both `Corn with Common Rust` and `Corn_(maize)___Common_rust_` into `{crop, disease, key}`. |
| `model.py` | ONNX session, preprocessing, softmax, top-k. |
| `advice.py` | Merge type-level IPM defaults with disease notes, then add confidence and a disclaimer. |
| `data/treatments.json` | 5 IPM defaults and 26 disease entries. |
| `server.py` | Mobile-first upload UI and `/api/diagnose`. |
| `cli.py` | `diagnose`, `serve`, and `doctor`. |

## Label contract

Every model label must normalize to a stable key: `{crop_slug}_{disease_slug}`.
That key joins the model output to `treatments.json`.

Examples:

```
Corn_(maize)___Common_rust_   -> maize_common_rust
Tomato___Late_blight          -> tomato_late_blight
Pepper,_bell___Bacterial_spot -> pepper_bacterial_spot
Apple___healthy               -> apple_healthy
```

## Adding a crop or disease

1. Add the class name to the model `config.json`, or fine-tune and export a new model.
2. Confirm that `parse_label()` produces a sensible key. Add an alias if it does not.
3. Add an entry under `diseases` in `treatments.json`, or let it fall back to the type defaults: fungal, bacterial, viral, pest, or healthy.
4. Add a fixture image and a test that asserts the crop.

## Deployment

- Laptop or clinic PC: run `shamba serve`. CPU is enough.
- Jetson Orin Nano: ONNX Runtime on CPU works. You can also install the TensorRT execution provider and export a 224x224 engine for lower latency.
- Android: export the same ONNX graph to ONNX Runtime Mobile or TFLite. The preprocessing contract does not change.
- Raspberry Pi: use `--variant mobilenet` (8.8 MB) and accept lower accuracy.

## Evaluation plan

- PlantVillage held-out split: top-1, top-3, and per-class recall.
- Field set: 200 consented photos from 3 regions, labelled by extension officers.
- Calibration: bucket predictions by confidence and compare with observed accuracy.
- Failure analysis: nutrient deficiency, herbicide damage, and mixed infections.
