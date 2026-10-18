from shamba.advice import get_advice
from shamba.labels import parse_label
from shamba.model import Prediction


def test_maize_rust_advice():
    prediction = Prediction(parse_label("Corn (Maize) with Common Rust"), 0.93)
    advice = get_advice(prediction)
    assert advice["crop"] == "Maize"
    assert "rust" in advice["summary"].lower() or "pustules" in advice["summary"].lower()
    assert advice["act_now"]
    assert advice["disclaimer"]


def test_low_confidence_note():
    prediction = Prediction(parse_label("Tomato with Late Blight"), 0.41)
    advice = get_advice(prediction)
    assert "confidence_note" in advice


def test_healthy_advice():
    prediction = Prediction(parse_label("Healthy Tomato Plant"), 0.99)
    advice = get_advice(prediction)
    assert advice["healthy"] is True
    assert "healthy" in advice["summary"].lower()


def test_fallback_type_inference():
    prediction = Prediction(parse_label("Tomato Mosaic Virus"), 0.8)
    advice = get_advice(prediction)
    assert advice["type"] == "viral"
