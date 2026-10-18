"""Local web UI: upload a leaf photo, get a diagnosis and a plan."""

from __future__ import annotations

import io
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError

from . import history as history_store
from .advice import get_advice
from .model import ModelNotReady, PlantDiseaseModel

STATIC = Path(__file__).resolve().parent / "static"
MAX_UPLOAD = 12 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 40_000_000
state: dict[str, Any] = {"model": None, "error": None}
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        state["model"] = PlantDiseaseModel()
    except ModelNotReady as exc:
        state["error"] = str(exc)
    yield


app = FastAPI(title="shamba", version="0.2.3", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html", media_type="text/html")


@app.get("/healthz")
def health() -> dict[str, object]:
    return {"ok": state["model"] is not None, "error": state["error"]}


@app.get("/api/history")
def list_history() -> dict[str, object]:
    entries = history_store.load_history()
    return {
        "entries": [entry.as_dict() for entry in entries],
        "limit": history_store.history_limit(),
    }


@app.delete("/api/history")
def clear_history() -> dict[str, object]:
    return {"ok": True, "cleared": history_store.clear_history()}


@app.post("/api/diagnose")
async def diagnose(file: UploadFile = File(...), top_k: int = Form(3)) -> JSONResponse:
    model = state["model"]
    if model is None:
        raise HTTPException(status_code=503, detail=state["error"] or "model not ready")

    payload = await file.read(MAX_UPLOAD + 1)
    if len(payload) > MAX_UPLOAD:
        raise HTTPException(status_code=413, detail="image too large (max 12 MB)")

    try:
        image = Image.open(io.BytesIO(payload))
        image = ImageOps.exif_transpose(image)
        image.load()
    except Image.DecompressionBombError as exc:
        raise HTTPException(status_code=413, detail="image has too many pixels") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="not a readable image") from exc

    started = time.perf_counter()
    predictions = model.predict(image, top_k=min(max(top_k, 1), 5))
    elapsed = round((time.perf_counter() - started) * 1000)
    top = predictions[0]
    advice = get_advice(top)

    try:
        history_store.record_diagnosis(
            crop=top.info.crop,
            disease=top.info.disease,
            healthy=top.info.healthy,
            confidence=top.confidence,
            source=file.filename,
        )
    except Exception:  # history is best-effort; a diagnosis must still succeed
        logger.warning("could not save diagnosis history", exc_info=True)

    return JSONResponse(
        {
            "predictions": [prediction.as_dict() for prediction in predictions],
            "advice": advice,
            "took_ms": elapsed,
        }
    )
