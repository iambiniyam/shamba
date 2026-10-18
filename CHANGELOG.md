# Changelog

## 0.2.1 - 2026-10-18

- Bound image uploads to 12 MB.
- Limit images to 40 megapixels and return a readable error.
- Apply EXIF orientation before prediction.
- Keep the model check aligned with the uploaded file.

## 0.2.0 - 2026-10-18

- Rebuilt the web interface with a phone camera first flow, drag and drop, paste, preview, top-three cards, confidence bars, and treatment sections.
- Added automatic dark mode, keyboard access, loading states, error recovery, and mobile layouts.
- Model now reads mean and std from each model's `preprocessor_config.json`.
- Fixed a normalization bug that lowered MobileNetV2 top-1 accuracy from 0.921 to 0.597.
- Added a 114-image held-out evaluation for DINOv2 and MobileNetV2.
- DINOv2 scored 1.000 top-1 and 1.000 top-3 on the held-out sample.

## 0.1.1 - 2026-10-18

- Fix wheel builds by removing a duplicate data include.
- No behavior change.

## 0.1.0 - 2026-10-18

First public release.

- Initial working version.
- CLI and local web interface.
- Test suite and GitHub Actions workflow.
