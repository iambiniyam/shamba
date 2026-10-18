import pytest

from shamba.calibration import (
    accuracy,
    brier_score,
    evaluate_records,
    expected_calibration_error,
    threshold_curve,
)


def test_accuracy_and_brier():
    outcomes = [True, True, False]
    confidences = [0.9, 0.8, 0.2]
    assert accuracy(outcomes) == pytest.approx(2 / 3)
    assert brier_score(confidences, outcomes) == pytest.approx((0.01 + 0.04 + 0.04) / 3)


def test_perfect_confidence_has_zero_ece():
    assert expected_calibration_error([1.0, 1.0], [True, True]) == 0.0
    assert expected_calibration_error([0.0], [False]) == 0.0


def test_overconfidence_has_positive_ece():
    assert expected_calibration_error([0.9, 0.9, 0.9], [False, False, False]) > 0.8


def test_evaluate_records_per_class():
    records = [
        {"true": "Maize rust", "predicted": "Maize rust", "confidence": 0.9, "correct": True},
        {"true": "Maize rust", "predicted": "Maize rust", "confidence": 0.8, "correct": True},
        {"true": "Tomato blight", "predicted": "Maize rust", "confidence": 0.7, "correct": False},
    ]
    result = evaluate_records(records)
    assert result.count == 3
    assert result.per_class_recall == {"Maize rust": pytest.approx(1.0), "Tomato blight": 0.0}


def test_threshold_curve_coverage_and_accuracy():
    curve = threshold_curve([0.9, 0.8, 0.6], [True, True, False])
    assert curve["0.5"]["coverage"] == 1.0
    assert curve["0.5"]["accuracy"] == pytest.approx(2 / 3, abs=1e-3)
    assert curve["0.9"]["coverage"] == pytest.approx(1 / 3, abs=1e-3)
    assert curve["0.9"]["accuracy"] == 1.0
