# Plant model evaluation

This checks the two shamba model variants on held-out PlantVillage images and records a preprocessing bug that the check found.

## Data

- 38 classes across 14 crops.
- 3 images per class, 114 images total.
- Images come from the PlantVillage `raw/color` set.
- The last three images in each class folder were used, avoiding the sample images in `tests/fixtures`.

The images are downloaded by `benchmarks/evaluate.py` setup, not committed. See `.gitignore`.

## Method

1. Load the model.
2. Map each class folder to a model label by token overlap.
3. Predict the top three classes for each image.
4. Compare the top-1 and top-3 predictions with the folder label.
5. Report accuracy and average latency on CPU.

Commands:

```bash
# DINOv2-small, the default
python benchmarks/evaluate.py

# MobileNetV2, the lightweight variant
python benchmarks/evaluate.py --model models/plant-disease/model.onnx --out docs/evaluation-mobilenet.json
```

## Results

| Model | Size | Top-1 | Top-3 | Latency |
|---|---|---|---|---|
| DINOv2-small | 84 MB | 1.000 | 1.000 | 133.9 ms |
| MobileNetV2 | 8.8 MB | 0.921 | 1.000 | 15.6 ms |

DINOv2 gets every held-out image right. MobileNetV2 misses nine images, mostly healthy leaves and similar tomato diseases, but keeps the correct class in the top three for all of them.

## The preprocessing bug

The first run of this benchmark scored 0.5965 top-1. The cause was normalization.

- The MobileNetV2 model card uses mean and std of `0.5`.
- The code used ImageNet mean and std for every model.
- On the MobileNetV2 weights, that mismatch dropped top-1 from 0.921 to 0.5965.
- DINOv2 uses ImageNet mean and std, so the old code happened to be right for DINOv2 and wrong for MobileNetV2.

The model now reads `preprocessor_config.json` next to the weights and uses its `image_mean` and `image_std`. Both variants score correctly.

This is why the benchmark exists. The tests passed before the fix because they only checked that a prediction was returned, not that it was the right one.

## Caveats

- Three images per class is a smoke test, not a full benchmark.
- The images are lab-style PlantVillage photos. Field photos with soil, shadows, and multiple leaves are harder.
- The model card reports 98.86% top-1 on a larger held-out split. Our 100% result is a small sample.
- Class folder mapping is automatic and could mislabel an ambiguous class. The per-image rows are in `docs/evaluation.json`.

## Reproduce

`docs/evaluation.json` and `docs/evaluation-mobilenet.json` contain every prediction, confidence, and the folder-to-label mapping.


## Calibration report

`shamba evaluate ./labeled-folder` measures top-1 accuracy, expected calibration error, Brier score, and per-class recall. The folder layout is one directory per class name, with images inside.

The tool is shipped without a dataset. A two-image smoke test on the bundled fixtures produced 0% accuracy, which is a warning about those fixtures, not a claim about the model on a real field set. A proper field-photo evaluation remains open.
