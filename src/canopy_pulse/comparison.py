"""Retrieve real public comparison rasters by COG range reads; no simulated layers."""

import json, math
from pathlib import Path
from datetime import datetime, timezone
import requests
import numpy as np
import rasterio
from rasterio.windows import from_bounds, Window
from rasterio.warp import transform_bounds, reproject, Resampling
from rasterio.transform import from_origin
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from .raster import sha256
from .science import power_db

import os

ROOT = Path(
    os.environ.get("OXYGEN_WORKSPACE_ROOT", Path(__file__).resolve().parents[2])
)
BBOX = [140.45, -34.55, 140.95, -34.15]
CRS = "EPSG:32754"
bounds = transform_bounds("EPSG:4326", CRS, *BBOX, densify_pts=21)
left, bottom, right, top = [
    math.floor(bounds[0] / 20) * 20,
    math.floor(bounds[1] / 20) * 20,
    math.ceil(bounds[2] / 20) * 20,
    math.ceil(bounds[3] / 20) * 20,
]
TRANSFORM = from_origin(left, top, 20, 20)
SHAPE = (round((top - bottom) / 20), round((right - left) / 20))


def write(path, array):
    with rasterio.open(
        path,
        "w",
        driver="COG",
        height=SHAPE[0],
        width=SHAPE[1],
        count=1,
        dtype="float32",
        crs=CRS,
        transform=TRANSFORM,
        nodata=np.nan,
        compress="DEFLATE",
    ) as ds:
        ds.write(array.astype("float32"), 1)


def subset(item, band, radar=False, signed=False):
    asset = item["assets"][band]
    url = asset["href"]
    if radar or signed:
        r = requests.get(
            "https://planetarycomputer.microsoft.com/api/sas/v1/sign",
            params={"href": url},
            timeout=60,
        )
        r.raise_for_status()
        url = r.json()["href"]
    with rasterio.Env(
        GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
        CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif,.tiff",
        GDAL_HTTP_TIMEOUT="90",
    ):
        with rasterio.open(url) as ds:
            b = transform_bounds("EPSG:4326", ds.crs, *BBOX, densify_pts=21)
            w = (
                from_bounds(*b, ds.transform)
                .round_offsets()
                .round_lengths()
                .intersection(Window(0, 0, ds.width, ds.height))
            )
            a = ds.read(1, window=w, masked=True).astype("float32").filled(np.nan)
            if radar:
                a[~np.isfinite(a) | (a <= 0)] = np.nan
            result = np.full(SHAPE, np.nan, dtype="float32")
            reproject(
                a,
                result,
                src_transform=ds.window_transform(w),
                src_crs=ds.crs,
                src_nodata=np.nan,
                dst_transform=TRANSFORM,
                dst_crs=CRS,
                dst_nodata=np.nan,
                resampling=Resampling.average if radar else Resampling.nearest,
            )
    return result


def main():
    out = ROOT / "outputs/comparison"
    out.mkdir(exist_ok=True)
    raw = ROOT / "data/raw/comparison"
    raw.mkdir(parents=True, exist_ok=True)
    manifest = []
    arrays = {}
    for catalog, dates, bands in [
        ("sentinel1rtc", ["20260821", "20260926", "20261008"], ["vv", "vh"]),
        ("sentinel2", ["20260823", "20260929", "20261007"], ["scl"]),
    ]:
        features = json.loads(
            (ROOT / f"data/acquisition/{catalog}_stac.json").read_text()
        )["features"]
        for date in dates:
            optical_platform = {
                "20260823": "S2B_",
                "20260929": "S2A_",
                "20261007": "S2C_",
            }
            items = [
                f
                for f in features
                if date in f["id"]
                and (
                    catalog == "sentinel1rtc"
                    or f["id"].startswith(optical_platform[date])
                )
            ]
            if catalog == "sentinel1rtc":
                if len(items) != 1:
                    raise ValueError("Ambiguous RTC scene")
                props = items[0]["properties"]
                if (
                    props["sat:relative_orbit"],
                    props["sat:orbit_state"],
                    props["platform"],
                ) != (162, "descending", "sentinel-1d"):
                    raise ValueError("RTC geometry mismatch")
            for band in bands:
                mosaic = np.full(SHAPE, np.nan, dtype="float32")
                for item in items:
                    path = raw / (item["id"] + "_" + band + ".tif")
                    if path.exists():
                        with rasterio.open(path) as ds:
                            a = ds.read(1)
                    else:
                        a = subset(item, band, catalog == "sentinel1rtc")
                        write(path, a)
                    valid = np.isfinite(a)
                    if band == "scl":
                        valid &= a != 0
                    mosaic[valid] = a[valid]
                    manifest.append(
                        dict(
                            item_id=item["id"],
                            datetime=item["properties"]["datetime"],
                            band=band,
                            source_url=item["assets"][band]["href"],
                            path=str(path.relative_to(ROOT)),
                            sha256=sha256(path),
                            resampling="linear-power average"
                            if catalog == "sentinel1rtc"
                            else "nearest categorical",
                            grid={
                                "crs": CRS,
                                "transform": list(TRANSFORM),
                                "shape": SHAPE,
                            },
                            source_asset=item["assets"][band],
                        )
                    )
                    print(
                        "Retrieved",
                        item["id"],
                        band,
                        int(valid.sum()),
                        "valid pixels",
                        flush=True,
                    )
                arrays[(catalog, date, band)] = mosaic
                write(out / f"{catalog}_{date}_{band}.tif", mosaic)
                (out / "input_manifest.json").write_text(json.dumps(manifest, indent=2))
    result = {
        "state": "IMPLEMENTED BUT UNVALIDATED",
        "scope": "Broad search box, not a mapped floodplain boundary",
        "nisar_advantage": None,
        "independent_subcanopy_validation": None,
        "sentinel1": {},
        "sentinel2": {},
    }
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    for col, date in enumerate(["20260821", "20260926", "20261008"]):
        a = arrays[("sentinel1rtc", date, "vv")]
        db = power_db(a)
        im = axes[0, col].imshow(db, vmin=-25, vmax=0, cmap="gray")
        axes[0, col].set_title("S1 VV gamma0 dB " + date)
        fig.colorbar(im, ax=axes[0, col], label="dB", fraction=0.046, pad=0.04)
        result["sentinel1"][date] = {
            "valid_pixels": int(np.isfinite(a).sum()),
            "median_vv_db": float(np.nanmedian(db)),
        }
    for col, date in enumerate(["20260823", "20260929", "20261007"]):
        a = arrays[("sentinel2", date, "scl")]
        clear = np.isin(a, [4, 5, 6])
        water = a == 6
        display = np.where(clear, np.where(water, 1, 0), np.nan)
        cmap = ListedColormap(["#eeeecc", "#1767a0"])
        cmap.set_bad("#555555")
        axes[1, col].imshow(display, vmin=0, vmax=1, cmap=cmap)
        axes[1, col].set_title(
            "S2 SCL " + date + (" (partial)" if date == "20261007" else "")
        )
        result["sentinel2"][date] = {
            "clear_pixels": int(clear.sum()),
            "water_label_pixels": int(water.sum()),
            "water_label_area_km2": float(water.sum() * 400 / 1e6),
        }
    for ax in axes.flat:
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle(
        "Actual conventional observations — 20 m analysis grid\nSCL labels do not validate subcanopy inundation; dates differ from NISAR",
        fontsize=14,
    )
    fig.legend(
        handles=[
            Patch(color="#eeeecc", label="Clear SCL land"),
            Patch(color="#1767a0", label="SCL water label"),
            Patch(color="#555555", label="Not clear / missing"),
        ],
        loc="lower center",
        ncol=3,
    )
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(out / "conventional_observations.png", dpi=160)
    plt.close(fig)
    for band in ["vv", "vh"]:
        a = arrays[("sentinel1rtc", "20260821", band)]
        b = arrays[("sentinel1rtc", "20261008", band)]
        delta = power_db(b) - power_db(a)
        write(out / f"sentinel1_{band}_change_db.tif", delta)
        result["sentinel1"][band + "_change"] = {
            "median_db": float(np.nanmedian(delta)),
            "quantiles_db": np.nanpercentile(delta, [5, 25, 50, 75, 95]).tolist(),
            "joint_valid_pixels": int(np.isfinite(delta).sum()),
        }
    a = arrays[("sentinel2", "20260823", "scl")]
    b = arrays[("sentinel2", "20260929", "scl")]
    common = np.isin(a, [4, 5, 6]) & np.isin(b, [4, 5, 6])
    result["sentinel2"]["paired_clear"] = {
        "dates": ["20260823", "20260929"],
        "pixels": int(common.sum()),
        "water_label_gain_km2": float(((a != 6) & (b == 6) & common).sum() * 400 / 1e6),
        "water_label_loss_km2": float(((a == 6) & (b != 6) & common).sum() * 400 / 1e6),
    }
    (out / "results.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
