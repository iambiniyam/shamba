from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from shamba import history, server
from shamba.labels import parse_label
from shamba.model import Prediction
from shamba.server import app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def isolated_history(tmp_path, monkeypatch):
    path = tmp_path / "history.json"
    monkeypatch.setenv(history.HISTORY_PATH_ENV, str(path))
    monkeypatch.delenv(history.HISTORY_LIMIT_ENV, raising=False)
    return path


class FakeModel:
    def predict(self, image, top_k=3):
        return [Prediction(parse_label("Corn (Maize) with Common Rust"), 0.93)]


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert "ok" in response.json()


def test_history_endpoints_do_not_require_model(monkeypatch):
    monkeypatch.setitem(server.state, "model", None)
    history.record_diagnosis(
        crop="Tomato",
        disease="Late Blight",
        healthy=False,
        confidence=0.81,
        source="tomato.jpg",
        timestamp="2026-05-01T10:00:00Z",
    )

    client = TestClient(app)
    listed = client.get("/api/history")
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["limit"] == history.DEFAULT_LIMIT
    assert [entry["source"] for entry in payload["entries"]] == ["tomato.jpg"]

    cleared = client.delete("/api/history")
    assert cleared.status_code == 200
    assert cleared.json() == {"ok": True, "cleared": 1}
    assert client.get("/api/history").json()["entries"] == []


def test_diagnose_records_history(monkeypatch):
    monkeypatch.setitem(server.state, "model", FakeModel())
    image = (FIXTURES / "maize_rust.jpg").read_bytes()

    client = TestClient(app)
    response = client.post(
        "/api/diagnose",
        files={"file": ("field_maize.jpg", image, "image/jpeg")},
        data={"top_k": "3"},
    )
    assert response.status_code == 200
    assert response.json()["predictions"][0]["crop"] == "Maize"

    entries = history.load_history()
    assert len(entries) == 1
    assert entries[0].crop == "Maize"
    assert entries[0].disease == "Common Rust"
    assert entries[0].healthy is False
    assert entries[0].source == "field_maize.jpg"
    assert entries[0].confidence == pytest.approx(0.93)


def test_diagnosis_succeeds_when_history_write_fails(monkeypatch):
    monkeypatch.setitem(server.state, "model", FakeModel())

    def fail(**kwargs):
        raise OSError("disk is read-only")

    monkeypatch.setattr(server.history_store, "record_diagnosis", fail)
    image = (FIXTURES / "maize_rust.jpg").read_bytes()

    client = TestClient(app)
    response = client.post(
        "/api/diagnose",
        files={"file": ("field_maize.jpg", image, "image/jpeg")},
    )
    assert response.status_code == 200
    assert response.json()["advice"]["crop"] == "Maize"
