"""Local web UI: upload a leaf photo, get a diagnosis and a plan."""

from __future__ import annotations

import io
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from PIL import Image, UnidentifiedImageError

from .advice import get_advice
from .model import ModelNotReady, PlantDiseaseModel

state: dict[str, Any] = {"model": None, "error": None}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        state["model"] = PlantDiseaseModel()
    except ModelNotReady as exc:
        state["error"] = str(exc)
    yield


app = FastAPI(title="shamba", version="0.1.0", lifespan=lifespan)

INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>shamba: crop doctor</title>
<style>
  :root { color-scheme: light dark; --green:#1f7a4d; --ink:#14261c; --paper:#f6f4ea; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
         background: var(--paper); color: var(--ink); }
  header { padding: 28px 20px 8px; max-width: 760px; margin: 0 auto; }
  h1 { font-size: 2rem; margin: 0 0 4px; letter-spacing: -0.03em; }
  .sub { color:#4d5f54; margin:0 0 18px; }
  main { max-width: 760px; margin: 0 auto; padding: 0 20px 48px; }
  .card { background:#fff; border:1px solid #d9d5c6; border-radius:16px; padding:18px;
          box-shadow: 0 6px 20px rgba(20,38,28,.06); margin-bottom:16px; }
  label.drop { display:block; border:2px dashed #9bb5a5; border-radius:12px; padding:22px;
               text-align:center; cursor:pointer; background:#fbfaf3; }
  label.drop:hover { border-color: var(--green); }
  input[type=file] { display:none; }
  button { background: var(--green); color:#fff; border:0; border-radius:10px;
           padding:12px 18px; font-size:1rem; font-weight:600; cursor:pointer; margin-top:12px; }
  button:disabled { opacity:.55; cursor:wait; }
  img.preview { max-width:100%; border-radius:12px; margin-top:12px; display:none; }
  .verdict { font-size:1.4rem; font-weight:700; margin:2px 0 2px; }
  .conf { color:#4d5f54; }
  .tag { display:inline-block; background:#e7f0ea; color:var(--green); border-radius:999px;
         padding:3px 10px; font-size:.8rem; font-weight:600; }
  h3 { margin:18px 0 6px; font-size:.95rem; text-transform:uppercase; letter-spacing:.06em; color:#3d5245; }
  ul { margin:6px 0 0; padding-left:18px; }
  li { margin:4px 0; line-height:1.45; }
  .muted { color:#6b7c71; font-size:.85rem; }
  .error { color:#a3322b; }
  .low { background:#fff5d6; border:1px solid #e8cf86; padding:10px 12px; border-radius:10px; margin-top:10px; }
</style>
</head>
<body>
<header>
  <h1>shamba</h1>
  <p class="sub">Offline crop doctor. Take one clear leaf photo and get a diagnosis and a plan.</p>
</header>
<main>
  <form id="form" class="card">
    <label class="drop" for="file">
      <strong>Choose or take a photo</strong><br>
      <span class="muted">JPG or PNG · fill the frame with one leaf · daylight is best</span>
    </label>
    <input id="file" name="file" type="file" accept="image/*" capture="environment" required>
    <img id="preview" class="preview" alt="leaf preview">
    <div><button id="go" type="submit">Diagnose</button></div>
  </form>
  <div id="out"></div>
</main>
<script>
const form = document.getElementById('form');
const fileInput = document.getElementById('file');
const preview = document.getElementById('preview');
const out = document.getElementById('out');
const go = document.getElementById('go');

fileInput.addEventListener('change', () => {
  const f = fileInput.files[0];
  if (!f) return;
  preview.src = URL.createObjectURL(f);
  preview.style.display = 'block';
});

function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

function section(title, items) {
  if (!items || !items.length) return '';
  return `<h3>${esc(title)}</h3><ul>${items.map(i => `<li>${esc(i)}</li>`).join('')}</ul>`;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const f = fileInput.files[0];
  if (!f) return;
  go.disabled = true; go.textContent = 'Reading the leaf...';
  out.innerHTML = '';
  const fd = new FormData(); fd.append('file', f); fd.append('top_k', '3');
  try {
    const res = await fetch('/api/diagnose', { method: 'POST', body: fd });
    if (!res.ok) throw new Error((await res.json()).detail || 'diagnosis failed');
    const data = await res.json();
    const a = data.advice;
    const top = data.predictions[0];
    out.innerHTML = `
      <div class="card">
        <span class="tag">${esc(a.healthy ? 'healthy' : 'possible disease')}</span>
        <div class="verdict">${esc(a.crop)} · ${esc(a.disease)}</div>
        <div class="conf">${(top.confidence * 100).toFixed(1)}% confidence</div>
        ${a.confidence_note ? `<div class="low">${esc(a.confidence_note)}</div>` : ''}
        <p>${esc(a.summary)}</p>
        ${section('Do now', a.act_now)}
        ${section('Low-cost / organic', a.organic)}
        ${section('Chemical (only if needed)', a.chemical)}
        ${section('Prevent next season', a.prevent)}
        ${a.escalate ? `<h3>When to escalate</h3><p>${esc(a.escalate)}</p>` : ''}
        <p class="muted">${esc(a.disclaimer)}</p>
      </div>`;
  } catch (err) {
    out.innerHTML = `<div class="card error">${esc(err.message)}</div>`;
  } finally {
    go.disabled = false; go.textContent = 'Diagnose';
  }
});
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


@app.get("/healthz")
def health() -> dict[str, Any]:
    return {"ok": state["model"] is not None, "error": state["error"]}


@app.post("/api/diagnose")
async def diagnose(file: UploadFile = File(...), top_k: int = Form(3)) -> dict[str, Any]:
    model = state["model"]
    if model is None:
        raise HTTPException(status_code=503, detail=state["error"] or "model not ready")

    payload = await file.read()
    if len(payload) > 12 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="image too large (max 12 MB)")

    try:
        image = Image.open(io.BytesIO(payload))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="not a readable image") from exc

    predictions = model.predict(image, top_k=min(max(top_k, 1), 5))
    return {
        "predictions": [p.as_dict() for p in predictions],
        "advice": get_advice(predictions[0]),
    }
