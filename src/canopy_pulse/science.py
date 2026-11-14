"""Conservative calculations. Unit tests establish code behavior, not environmental validity."""

import numpy as np
from scipy.ndimage import label

COMPATIBILITY = (
    "track",
    "frame",
    "direction",
    "polarizations",
    "bandwidth",
    "crid",
    "product_version",
    "collection",
)


def assert_compatible(a, b):
    for key in COMPATIBILITY:
        if key not in a or key not in b or a[key] is None or b[key] is None:
            raise ValueError(f"Missing compatibility metadata: {key}")
        if a[key] != b[key]:
            raise ValueError(f"Incompatible {key}: {a[key]} != {b[key]}")
    if a.get("start") == b.get("start"):
        raise ValueError("Duplicate acquisition time is not a repeat observation")


def power_db(power):
    x = np.asarray(power, dtype=float)
    out = np.full(x.shape, np.nan)
    valid = np.isfinite(x) & (x > 0)
    out[valid] = 10 * np.log10(x[valid])
    return out


def valid_pixels(power, mask, looks):
    """GCOV subswath mask: 0 invalid, 255 fill; require positive finite looks.

    Caller must verify the mask description matches the documented GCOV convention.
    """
    p, m, n = map(np.asarray, (power, mask, looks))
    if p.shape != m.shape or p.shape != n.shape:
        raise ValueError("Layer shapes differ")
    return (
        np.isfinite(p)
        & (p > 0)
        & np.isfinite(m)
        & (m >= 1)
        & (m <= 5)
        & (m == np.floor(m))
        & np.isfinite(n)
        & (n > 0)
    )


def block_power(power, valid, factor):
    if not isinstance(factor, int) or factor < 1:
        raise ValueError("Factor must be a positive integer")
    p = np.asarray(power, dtype=float)
    if p.ndim != 2 or p.shape != np.shape(valid):
        raise ValueError("Expected matching 2D power and validity")
    h, w = p.shape
    if h % factor or w % factor:
        raise ValueError("Shape must be divisible by factor; no silent edge dropping")
    p = np.where(valid & np.isfinite(p) & (p > 0), p, 0)
    v = valid & (p > 0)
    shape = (h // factor, factor, w // factor, factor)
    count = v.reshape(shape).sum(axis=(1, 3))
    total = p.reshape(shape).sum(axis=(1, 3))
    mean = np.divide(total, count, out=np.full(total.shape, np.nan), where=count > 0)
    return mean, count / factor**2


def change(before, after, valid_before, valid_after):
    if not (
        np.shape(before)
        == np.shape(after)
        == np.shape(valid_before)
        == np.shape(valid_after)
    ):
        raise ValueError("Unaligned shapes")
    return np.where(
        valid_before & valid_after, power_db(after) - power_db(before), np.nan
    )


def regions(candidate, pixel_area_m2):
    if not np.isfinite(pixel_area_m2) or pixel_area_m2 <= 0:
        raise ValueError("Positive projected pixel area required")
    labels, n = label(np.asarray(candidate, bool))
    return labels, [
        {"id": i, "area_m2": int((labels == i).sum()) * pixel_area_m2}
        for i in range(1, n + 1)
    ]


def detection_metrics(reference, predicted):
    y, p = np.asarray(reference), np.asarray(predicted)
    if (
        y.shape != p.shape
        or y.size == 0
        or not np.isin(y, [0, 1]).all()
        or not np.isin(p, [0, 1]).all()
    ):
        raise ValueError("Nonempty aligned binary labels required")
    tp, fp = int(((y == 1) & (p == 1)).sum()), int(((y == 0) & (p == 1)).sum())
    fn, tn = int(((y == 1) & (p == 0)).sum()), int(((y == 0) & (p == 0)).sum())
    div = lambda a, b: a / b if b else None
    return dict(
        tp=tp,
        fp=fp,
        fn=fn,
        tn=tn,
        precision=div(tp, tp + fp),
        recall=div(tp, tp + fn),
        f1=div(2 * tp, 2 * tp + fp + fn),
        iou=div(tp, tp + fp + fn),
    )


def information_gain(covariance, noise_variance):
    """Single noisy scalar observation of a Gaussian latent field: I=0.5 log(1+var/noise).

    Requires an externally calibrated covariance; does not manufacture one from radar.
    """
    c = np.asarray(covariance, float)
    if (
        c.ndim != 2
        or c.shape[0] != c.shape[1]
        or not np.isfinite(c).all()
        or not np.allclose(c, c.T)
    ):
        raise ValueError("Finite symmetric covariance required")
    if (
        np.linalg.eigvalsh(c).min() < -1e-10
        or not np.isfinite(noise_variance)
        or noise_variance <= 0
    ):
        raise ValueError("Positive noise and positive semidefinite covariance required")
    return 0.5 * np.log1p(np.maximum(np.diag(c), 0) / noise_variance)
