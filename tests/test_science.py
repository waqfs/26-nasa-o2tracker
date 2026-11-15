import numpy as np
import pytest
from canopy_pulse.science import (
    power_db,
    valid_pixels,
    block_power,
    change,
    assert_compatible,
    detection_metrics,
    regions,
    information_gain,
)


def test_db_invalid_and_scale():
    np.testing.assert_allclose(power_db([1, 10, 0.1]), [0, 10, -10])
    assert np.isnan(power_db([0, -1, np.inf, np.nan])).all()


def test_mask_codes_and_looks():
    assert valid_pixels(
        [1] * 6, [0, 1, 2, 255, 1.5, 3], [1, 1, 1, 1, 1, 0]
    ).tolist() == [False, True, True, False, False, False]
    assert valid_pixels([1] * 3, [5, 6, 254], [1] * 3).tolist() == [True, False, False]


def test_power_aggregation_not_db_average():
    p, coverage = block_power(np.array([[1, 100], [1, 100]]), np.ones((2, 2), bool), 2)
    assert p.item() == 50.5
    assert power_db(p).item() != 10
    assert coverage.item() == 1


def test_missing_block():
    p, c = block_power(np.ones((2, 2)), np.zeros((2, 2), bool), 2)
    assert np.isnan(p.item()) and c.item() == 0


def test_change_known_ratio_and_mask():
    result = change(
        np.array([1, 2]),
        np.array([10, 4]),
        np.array([True, False]),
        np.array([True, True]),
    )
    assert result[0] == 10 and np.isnan(result[1])


@pytest.mark.parametrize(
    "key",
    [
        "crid",
        "track",
        "frame",
        "direction",
        "polarizations",
        "bandwidth",
        "product_version",
        "collection",
    ],
)
def test_compatibility_rejects_changes(key):
    a = dict(
        track="153",
        frame="160",
        direction="ASCENDING",
        polarizations=["HH", "HV"],
        bandwidth="20",
        crid="P05023",
        product_version="1.0.11",
        collection="provisional",
        start="a",
    )
    b = {**a, "start": "b", key: "different"}
    with pytest.raises(ValueError):
        assert_compatible(a, b)


def test_duplicate_rejected():
    a = dict(
        track="153",
        frame="160",
        direction="A",
        polarizations=["HH"],
        bandwidth="20",
        crid="P05023",
        product_version="1",
        collection="p",
        start="a",
    )
    with pytest.raises(ValueError):
        assert_compatible(a, a)


def test_metrics_and_undefined():
    m = detection_metrics([1, 1, 0, 0], [1, 0, 1, 0])
    assert m["f1"] == 0.5 and m["iou"] == 1 / 3
    assert detection_metrics([0], [0])["recall"] is None
    with pytest.raises(ValueError):
        detection_metrics([], [])


def test_regions_area():
    _, r = regions([[1, 0], [0, 1]], 400)
    assert len(r) == 2 and sum(x["area_m2"] for x in r) == 800


def test_information_gain():
    np.testing.assert_allclose(
        information_gain([[1, 0], [0, 4]], 1), 0.5 * np.log([2, 5])
    )
    with pytest.raises(ValueError):
        information_gain([[1, 2], [2, 1]], 1)


def test_shape_guards():
    with pytest.raises(ValueError):
        valid_pixels([1, 2], [1], [1])
    with pytest.raises(ValueError):
        block_power(np.ones((3, 3)), np.ones((3, 3), bool), 2)
