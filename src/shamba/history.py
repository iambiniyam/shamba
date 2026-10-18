"""Bounded, metadata-only diagnosis history stored on this device."""

from __future__ import annotations

import contextlib
import json
import math
import os
import tempfile
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LIMIT = 20
MAX_LIMIT = 500
HISTORY_PATH_ENV = "SHAMBA_HISTORY_PATH"
HISTORY_LIMIT_ENV = "SHAMBA_HISTORY_LIMIT"
ENTRY_FIELDS = ("timestamp", "crop", "disease", "healthy", "confidence", "source")
_MAX_TEXT = 120
_MAX_TIMESTAMP = 64
_LOCK = threading.Lock()

__all__ = [
    "DEFAULT_LIMIT",
    "ENTRY_FIELDS",
    "HISTORY_LIMIT_ENV",
    "HISTORY_PATH_ENV",
    "MAX_LIMIT",
    "HistoryEntry",
    "clear_history",
    "history_limit",
    "history_path",
    "load_history",
    "record_diagnosis",
]


@dataclass(frozen=True, slots=True)
class HistoryEntry:
    """One diagnosis summary. Deliberately excludes image data and paths."""

    timestamp: str
    crop: str
    disease: str
    healthy: bool
    confidence: float
    source: str

    def as_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "crop": self.crop,
            "disease": self.disease,
            "healthy": self.healthy,
            "confidence": round(self.confidence, 4),
            "source": self.source,
        }


def history_path() -> Path:
    """Return the history file, honoring SHAMBA_HISTORY_PATH."""
    override = os.getenv(HISTORY_PATH_ENV)
    if override and override.strip():
        return Path(override).expanduser()
    return Path.home() / ".shamba" / "history.json"


def history_limit() -> int:
    """Return the maximum entry count, honoring SHAMBA_HISTORY_LIMIT."""
    raw = os.getenv(HISTORY_LIMIT_ENV, "").strip()
    if not raw:
        return DEFAULT_LIMIT
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_LIMIT
    return max(1, min(value, MAX_LIMIT))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _timestamp(value: datetime | str | None) -> str:
    if value is None:
        return _now()
    if isinstance(value, datetime):
        moment = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    text = str(value).strip()
    return text[:_MAX_TIMESTAMP] if text else _now()


def _clean_source(source: object) -> str:
    """Keep a printable file name only, never a directory path or image data."""
    text = str(source or "").replace("\\", "/").rsplit("/", 1)[-1]
    text = "".join(character for character in text if character.isprintable()).strip()
    return text[:255] or "unknown"


def _entry_from_mapping(raw: Mapping[str, object]) -> HistoryEntry | None:
    timestamp = raw.get("timestamp")
    crop = raw.get("crop")
    disease = raw.get("disease")
    healthy = raw.get("healthy")
    confidence = raw.get("confidence")
    if not isinstance(timestamp, str) or not isinstance(crop, str) or not isinstance(disease, str):
        return None
    if not isinstance(healthy, bool):
        return None
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return None
    value = float(confidence)
    if not math.isfinite(value):
        return None

    timestamp = timestamp.strip()[:_MAX_TIMESTAMP]
    crop = crop.strip()[:_MAX_TEXT]
    disease = disease.strip()[:_MAX_TEXT]
    if not timestamp or not crop or not disease:
        return None
    return HistoryEntry(
        timestamp=timestamp,
        crop=crop,
        disease=disease,
        healthy=healthy,
        confidence=max(0.0, min(value, 1.0)),
        source=_clean_source(raw.get("source")),
    )


def _read(path: Path) -> list[HistoryEntry]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if isinstance(raw, dict):
        raw = raw.get("entries")
    if not isinstance(raw, list):
        return []

    entries: list[HistoryEntry] = []
    for item in raw:
        if isinstance(item, Mapping):
            entry = _entry_from_mapping(item)
            if entry is not None:
                entries.append(entry)
    return entries


def _write(path: Path, entries: list[HistoryEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [entry.as_dict() for entry in entries]
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
        os.replace(temporary, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise


def load_history(limit: int | None = None) -> list[HistoryEntry]:
    """Return entries newest first. A missing or damaged file reads as empty."""
    bound = history_limit() if limit is None else max(0, int(limit))
    with _LOCK:
        entries = _read(history_path())
    return entries[:bound]


def record_diagnosis(
    *,
    crop: str,
    disease: str,
    healthy: bool,
    confidence: float,
    source: object = None,
    timestamp: datetime | str | None = None,
    limit: int | None = None,
) -> HistoryEntry:
    """Prepend one diagnosis and trim the file to the configured limit."""
    entry = _entry_from_mapping(
        {
            "timestamp": _timestamp(timestamp),
            "crop": crop,
            "disease": disease,
            "healthy": healthy,
            "confidence": confidence,
            "source": source,
        }
    )
    if entry is None:
        raise ValueError("invalid history entry")

    capacity = history_limit() if limit is None else max(1, int(limit))
    path = history_path()
    with _LOCK:
        entries = _read(path)
        entries.insert(0, entry)
        del entries[capacity:]
        _write(path, entries)
    return entry


def clear_history() -> int:
    """Delete the history file and return how many entries it held."""
    path = history_path()
    with _LOCK:
        entries = _read(path)
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    return len(entries)
