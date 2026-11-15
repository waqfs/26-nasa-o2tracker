import numpy as np
from canopy_pulse.validation_metrics import average_precision, acquired_before_label


def test_average_precision_ties_are_order_independent():
    labels = np.array([True, False, True, False])
    scores = np.ones(4)
    assert average_precision(labels, scores) == 0.5
    assert average_precision(labels[::-1], scores) == 0.5


def test_average_precision_threshold_integration():
    labels = np.array([True, False, True])
    assert abs(average_precision(labels, np.array([0.9, 0.8, 0.7])) - 5 / 6) < 1e-12


def test_september_feature_times_fail_prediction_gate():
    features = ["2026-09-26T19:56:34Z", "2026-09-28T20:34:56Z", "2026-09-29T00:46:56Z"]
    assert not acquired_before_label(features, "2026-09-24T00:27:21Z")
    assert acquired_before_label(features, "2026-10-02T00:27:28Z")
