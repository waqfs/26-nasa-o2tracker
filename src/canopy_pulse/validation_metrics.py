"""Metrics and chronology checks used by the submission audit."""

import numpy as np
from datetime import datetime


def average_precision(labels, scores):
    """Integrate precision at distinct score thresholds, giving tied scores one threshold."""
    order = np.argsort(-scores, kind="stable")
    sorted_scores = scores[order]
    positives = labels[order].astype(int).cumsum()
    ends = np.r_[np.flatnonzero(np.diff(sorted_scores)), len(labels) - 1]
    true_positive = positives[ends]
    precision = true_positive / (ends + 1)
    increments = np.diff(np.r_[0, true_positive]) / labels.sum()
    return float(increments @ precision)


def acquired_before_label(feature_times, label_time):
    """Observation-time gate only. Product availability requires a separate audit."""
    cutoff = datetime.fromisoformat(label_time.replace("Z", "+00:00"))
    return all(
        datetime.fromisoformat(t.replace("Z", "+00:00")) <= cutoff
        for t in feature_times
    )
