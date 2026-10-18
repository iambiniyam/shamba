import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
os.environ.setdefault("SHAMBA_MODEL_DIR", str(REPO / "models" / "dinov2"))
