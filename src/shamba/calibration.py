"""Calibration and accuracy metrics for a labeled local evaluation set."""

from __future__ import annotations

from dataclasses import dataclass


def accuracy(outcomes: list[bool]) -> float:
    return sum(outcomes) / len(outcomes) if outcomes else 0.0


def brier_score(confidences: list[float], outcomes: list[bool]) -> float:
    if not confidences:
        return 0.0
    return sum((confidence - (1.0 if outcome else 0.0)) ** 2 for confidence, outcome in zip(confidences, outcomes)) / len(confidences)


def expected_calibration_error(
    confidences: list[float],
    outcomes: list[bool],
    bins: int = 10,
) -> float:
    if not confidences:
        return 0.0
    total = len(confidences)
    error = 0.0
    for index in range(bins):
        low = index / bins
        high = (index + 1) / bins
        selected = [
            (confidence, outcome)
            for confidence, outcome in zip(confidences, outcomes)
            if low <= confidence < high or (index == bins - 1 and confidence == 1.0)
        ]
        if not selected:
            continue
        average = sum(confidence for confidence, _ in selected) / len(selected)
        observed = sum(1 for _, outcome in selected if outcome) / len(selected)
        error += (len(selected) / total) * abs(average - observed)
    return error


@dataclass(slots=True)
class Evaluation:
    count: int
    accuracy: float
    brier: float
    ece: float
    per_class_recall: dict[str, float]

    def as_dict(self) -> dict[str, object]:
        return {
            "count": self.count,
            "accuracy": round(self.accuracy, 4),
            "brier": round(self.brier, 4),
            "ece": round(self.ece, 4),
            "per_class_recall": {key: round(value, 4) for key, value in self.per_class_recall.items()},
        }


def evaluate_records(records: list[dict[str, object]]) -> Evaluation:
    """Summarize records with true, predicted, and confidence fields."""
    outcomes = [bool(item["correct"]) for item in records]
    confidences = [float(item["confidence"]) for item in records]
    by_class: dict[str, list[bool]] = {}
    for item in records:
        by_class.setdefault(str(item["true"]), []).append(bool(item["correct"]))
    return Evaluation(
        count=len(records),
        accuracy=accuracy(outcomes),
        brier=brier_score(confidences, outcomes),
        ece=expected_calibration_error(confidences, outcomes),
        per_class_recall={key: accuracy(values) for key, values in sorted(by_class.items())},
    )
