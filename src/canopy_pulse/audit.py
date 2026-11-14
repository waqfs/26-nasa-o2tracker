"""Descriptive radiometric/geometric audit. Reference classes are proxies, not calibration targets."""

import json
from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter
from scipy.signal import correlate
from .comparison import ROOT, SHAPE, TRANSFORM, CRS
from .raster import read_cogs, MASK_CONVENTION, sha256
from .science import power_db, block_power
from rasterio.warp import reproject, Resampling


def stats(a):
    v = a[np.isfinite(a)]
    return (
        dict(
            n=int(v.size),
            percentiles=np.percentile(v, [0, 5, 25, 50, 75, 95, 100]).tolist(),
        )
        if v.size
        else dict(n=0)
    )


def registration(a, b):
    # Independent 256x256 windows, high-pass log power. Integer search ±3 pixels.
    results = []
    for row in range(128, a.shape[0] - 300, 400):
        for col in range(128, a.shape[1] - 300, 400):
            x = a[row : row + 256, col : col + 256]
            y = b[row : row + 256, col : col + 256]
            if np.isfinite(x).mean() < 0.99 or np.isfinite(y).mean() < 0.99:
                continue
            x = np.nan_to_num(x, nan=np.nanmedian(x))
            y = np.nan_to_num(y, nan=np.nanmedian(y))
            x = gaussian_filter(x, 1) - gaussian_filter(x, 6)
            y = gaussian_filter(y, 1) - gaussian_filter(y, 6)
            scores = []
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    u = x[4:-4, 4:-4].ravel()
                    v = y[4 + dy : 252 + dy, 4 + dx : 252 + dx].ravel()
                    scores.append((float(np.corrcoef(u, v)[0, 1]), dy, dx))
            score, dy, dx = max(scores)
            zero = next(s[0] for s in scores if s[1:] == (0, 0))
            results.append(
                dict(
                    row=row,
                    col=col,
                    match_dy=dy,
                    match_dx=dx,
                    correlation=score,
                    zero_correlation=zero,
                )
            )
    return dict(
        method="High-pass log-power normalized correlation, 256px windows, integer search +/-3 native pixels. Not absolute geolocation or subpixel calibration.",
        windows=results,
    )


def main(workspace=None, output=None):
    root = Path(workspace) if workspace else ROOT
    out = Path(output) if output else root / "outputs/validation"
    out.mkdir(parents=True, exist_ok=True)
    jobs = json.loads((root / "data/acquisition/jobs.json").read_text())
    req = json.loads((root / "data/acquisition/request.json").read_text())
    arrays = {}
    qa = []
    native = {}
    for i, acq in enumerate(req["acquisitions"]):
        entries = {k: jobs[acq["concept_id"] + "_" + k] for k in req["variables"]}
        for e in entries.values():
            assert sha256(root / e["file"]["path"]) == e["file"]["sha256"]
        p = {k: root / e["file"]["path"] for k, e in entries.items()}
        for pol in ["HHHH", "HVHV"]:
            layer = read_cogs(p[pol], p["mask"], p["numberOfLooks"], MASK_CONVENTION)
            a = np.where(layer.valid, layer.power, np.nan)
            native[i, pol] = power_db(a)
            dst = np.full(SHAPE, np.nan, dtype="float32")
            reproject(
                a,
                dst,
                src_transform=layer.transform,
                src_crs=layer.crs,
                src_nodata=np.nan,
                dst_transform=TRANSFORM,
                dst_crs=CRS,
                dst_nodata=np.nan,
                resampling=Resampling.average,
            )
            arrays[i, pol] = dst
        qa.append(
            dict(
                concept_id=acq["concept_id"],
                attributes=acq["record"]["attributes"],
                looks=stats(np.where(layer.valid, layer.looks, np.nan)),
                mask_codes=np.unique(layer.mask[np.isfinite(layer.mask)]).tolist(),
            )
        )
    h, w = SHAPE[0] // 5 * 5, SHAPE[1] // 5 * 5
    common = np.logical_and.reduce([np.isfinite(a) & (a > 0) for a in arrays.values()])[
        :h, :w
    ]
    blocks = {}
    for k, a in arrays.items():
        blocks[k], coverage = block_power(a[:h, :w], common, 5)
    keep = coverage >= 0.8
    with rasterio.open(root / "data/raw/comparison/worldcover_2021.tif") as ds:
        lc = ds.read(1)[:h, :w]

    def fraction(a):
        return a.reshape(h // 5, 5, w // 5, 5).mean((1, 3))

    optical = []
    for d in ["20260823", "20260929"]:
        with rasterio.open(root / f"outputs/comparison/sentinel2_{d}_scl.tif") as ds:
            optical.append(ds.read(1)[:h, :w])
    dry = (fraction(np.isin(optical[0], [4, 5])) >= 0.9) & (
        fraction(np.isin(optical[1], [4, 5])) >= 0.9
    )
    strata = {
        name: (fraction(lc == code) >= 0.8) & keep & dry
        for code, name in [
            (50, "built_up_proxy"),
            (60, "bare_sparse_proxy"),
            (40, "cropland_not_stable"),
            (10, "tree_not_stable"),
            (20, "shrub_not_stable"),
        ]
    }
    changes = {}
    sensitivity = {}
    for first, last in [(0, 1), (1, 2), (0, 2)]:
        name = f"{first}_{last}"
        changes[name] = {}
        for pol in ["HHHH", "HVHV"]:
            delta = np.where(
                keep, power_db(blocks[last, pol]) - power_db(blocks[first, pol]), np.nan
            )
            changes[name][pol] = {
                "all": stats(delta),
                **{k: stats(delta[mask]) for k, mask in strata.items()},
            }
            if name == "0_1":
                sensitivity[pol] = {}
                for label in ["built_up_proxy", "bare_sparse_proxy"]:
                    mask = strata[label]
                    offset = float(np.nanmedian(delta[mask])) if mask.any() else None
                    sensitivity[pol][label] = dict(
                        offset_db=offset,
                        regional_median_after_subtraction=float(
                            np.nanmedian(delta) - offset
                        )
                        if offset is not None
                        else None,
                        interpretation="Sensitivity only: assumes reference proxy stable. Not an applied calibration correction.",
                    )
    result = dict(
        qa=qa,
        reference_selection="WorldCover 2021 >=80% class; >=90% SCL land on both dates. Chosen without radar-change filtering. Built/bare proxies may change; no corner reflectors or invariant targets.",
        changes_100m=changes,
        offset_sensitivity=sensitivity,
        registration={
            f"{i}_{j}_{pol}": registration(native[i, pol], native[j, pol])
            for i, j in [(0, 1), (1, 2), (0, 2)]
            for pol in ["HHHH", "HVHV"]
        },
        inference="Instrumental/processing effects cannot be excluded from a regional shift without invariant targets and per-acquisition calibration/quality metadata. Common grid does not establish subpixel registration.",
    )
    (out / "radar_audit.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({"changes": changes, "sensitivity": sensitivity}, indent=2))


if __name__ == "__main__":
    main()
