# Contributing

Thanks for taking a look. Small, focused pull requests are easiest to review.

## Development setup

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
python scripts/download_model.py
pytest -q
```

## Before opening a pull request

- Run the test suite.
- Add a test for any behavior change.
- Update the README if a command, flag, or output changes.

## Field photos

The most useful contribution is a set of field photos with expert labels. Open an issue first and describe the crop, the region, and the symptoms. Do not upload photos that you do not have permission to share.

## Bug reports

Include the command you ran, the Python version, the operating system, and the full error output. If the problem is a wrong prediction, attach a photo of the leaf if you can.
