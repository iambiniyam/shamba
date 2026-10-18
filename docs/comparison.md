# Comparison

## Similar tools

- [Plantix](https://plantix.net/) and [PlantVillage Nuru](https://plantvillage.psu.edu/) are phone-first crop diagnosis apps with large image libraries and agronomy content.
- They show the right shape: a photo, a likely cause, and an action plan.

## What shamba does differently

- Fully offline inference with a small ONNX model.
- Top-three alternatives and an explicit uncertainty state, not only a top label.
- A local calibration report with accuracy, ECE, Brier score, and per-class recall.
- Crop-specific advice with a safety boundary and a local diagnosis history.
- No account or upload.

## Tradeoff

Plantix and Nuru cover many more crops and field conditions. shamba is a focused local scanner for the classes in its model, and it should be treated as a first opinion, not an agronomist.
