# Third-party models and data

`shamba` code is MIT. The default model, the optional lightweight model, and the
training data carry their own licenses.

## Default: DINOv2-small + linear head

- Model: [`rodynaemad/plant-disease-dinov2-small`](https://huggingface.co/rodynaemad/plant-disease-dinov2-small)
- Base: [`facebook/dinov2-small`](https://huggingface.co/facebook/dinov2-small)
- License: **CC-BY-SA-4.0**
- Reported accuracy: 98.86% top-1 on a held-out PlantVillage split (10,862 photos)
- Shipped as ONNX (`onnx/model_with_features.onnx` → `model.onnx`)

If you redistribute a fine-tuned version, keep the CC-BY-SA attribution and
share-alike terms.

## Lightweight: MobileNetV2 PlantVillage classifier

- Model: [`onnx-community/mobilenet_v2_1.0_224-plant-disease-identification-ONNX`](https://huggingface.co/onnx-community/mobilenet_v2_1.0_224-plant-disease-identification-ONNX)
- Upstream fine-tune: [`linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification`](https://huggingface.co/linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification)
- License: see the upstream model cards
- Shipped as ONNX (`onnx/model.onnx` → `model.onnx`)

## Dataset

- [PlantVillage](https://github.com/spMohanty/PlantVillage-Dataset), Hughes & Salathé (2015).
- Images are lab-style single leaves. Check the dataset repository for its current
  license before redistributing images.

## Runtime

- ONNX Runtime (MIT), Pillow (HPND), NumPy (BSD-3-Clause).
