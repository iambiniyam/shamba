from __future__ import annotations

import json

import pytest

from shamba import history


@pytest.fixture(autouse=True)
def isolated_history(tmp_path, monkeypatch):
    path = tmp_path / "history.json"
    monkeypatch.setenv(history.HISTORY_PATH_ENV, str(path))
    monkeypatch.delenv(history.HISTORY_LIMIT_ENV, raising=False)
    return path


def make_entry(index: int, **overrides):
    values = {
        "crop": "Maize",
        "disease": "Common Rust",
        "healthy": False,
        "confidence": 0.93,
        "source": f"leaf-{index}.jpg",
        "timestamp": f"2026-01-01T00:00:{index:02d}Z",
    }
    values.update(overrides)
    return values


def test_record_and_load_round_trip(isolated_history):
    history.record_diagnosis(
        crop="Tomato",
        disease="Late Blight",
        healthy=False,
        confidence=0.91234,
        source="/tmp/photos/tomato-leaf.jpg",
        timestamp="2026-05-01T10:00:00Z",
    )

    entries = history.load_history()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.timestamp == "2026-05-01T10:00:00Z"
    assert entry.crop == "Tomato"
    assert entry.disease == "Late Blight"
    assert entry.healthy is False
    assert entry.confidence == pytest.approx(0.9123)
    assert entry.source == "tomato-leaf.jpg"

    raw = json.loads(isolated_history.read_text(encoding="utf-8"))
    assert len(raw) == 1
    assert set(raw[0]) == set(history.ENTRY_FIELDS)
    assert raw[0]["source"] == "tomato-leaf.jpg"
    assert raw[0]["timestamp"] == "2026-05-01T10:00:00Z"


def test_source_windows_path_is_reduced_to_filename(isolated_history):
    history.record_diagnosis(
        crop="Bean",
        disease="Healthy",
        healthy=True,
        confidence=0.8,
        source=r"C:\Users\bini\Pictures\leaf.jpg",
    )

    assert history.load_history()[0].source == "leaf.jpg"


def test_history_is_capped_at_default_limit(isolated_history):
    for index in range(25):
        history.record_diagnosis(**make_entry(index))

    entries = history.load_history()
    assert len(entries) == history.DEFAULT_LIMIT == 20
    assert [entry.source for entry in entries] == [
        f"leaf-{index}.jpg" for index in range(24, 4, -1)
    ]

    raw = json.loads(isolated_history.read_text(encoding="utf-8"))
    assert len(raw) == 20


def test_history_limit_can_be_overridden(isolated_history, monkeypatch):
    monkeypatch.setenv(history.HISTORY_LIMIT_ENV, "3")
    for index in range(5):
        history.record_diagnosis(**make_entry(index))

    assert [entry.source for entry in history.load_history()] == [
        "leaf-4.jpg",
        "leaf-3.jpg",
        "leaf-2.jpg",
    ]
    assert len(json.loads(isolated_history.read_text(encoding="utf-8"))) == 3


def test_history_persists_on_disk(isolated_history):
    history.record_diagnosis(**make_entry(7))

    assert isolated_history.exists()
    stored = json.loads(isolated_history.read_text(encoding="utf-8"))
    assert stored[0]["source"] == "leaf-7.jpg"
    assert [entry.as_dict() for entry in history.load_history()] == stored


def test_clear_history(isolated_history):
    for index in range(3):
        history.record_diagnosis(**make_entry(index))
    assert len(history.load_history()) == 3

    assert history.clear_history() == 3
    assert history.load_history() == []
    assert not isolated_history.exists()
    assert history.clear_history() == 0


def test_damaged_file_reads_as_empty_and_recovers(isolated_history):
    isolated_history.write_text("not json", encoding="utf-8")

    assert history.load_history() == []

    history.record_diagnosis(**make_entry(0))
    assert [entry.source for entry in history.load_history()] == ["leaf-0.jpg"]


def test_history_drops_unexpected_fields_and_paths(isolated_history):
    isolated_history.write_text(
        json.dumps(
            [
                {
                    "timestamp": "2026-05-01T10:00:00Z",
                    "crop": "Maize",
                    "disease": "Common Rust",
                    "healthy": False,
                    "confidence": 0.9,
                    "source": "/tmp/leaf.jpg",
                    "image": "data:image/jpeg;base64,AAAA",
                }
            ]
        ),
        encoding="utf-8",
    )

    entry = history.load_history()[0]
    assert entry.source == "leaf.jpg"
    assert not hasattr(entry, "image")
