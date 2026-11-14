"""Execute real-raster processing and a matched, descriptive multi-sensor comparison."""

import json, csv
from pathlib import Path
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from pyproj import Transformer
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .comparison import ROOT, SHAPE, TRANSFORM, CRS
from .raster import read_cogs, sha256, MASK_CONVENTION
from .science import power_db, block_power
from .process import run


def main():
    jobs = json.loads((ROOT / "data/acquisition/jobs.json").read_text())
    req = json.loads((ROOT / "data/acquisition/request.json").read_text())
    records = [r["record"] for r in req["acquisitions"]]
    out = ROOT / "outputs/real"
    out.mkdir(exist_ok=True)
    paths = {}
    qa = []
    for r in records:
        paths[r["granule_id"]] = {}
        for band in req["variables"]:
            entry = jobs.get(r["concept_id"] + "_" + band, {})
            if entry.get("status") != "successful" or "file" not in entry:
                raise RuntimeError(
                    "Awaiting completed science/QA layer: "
                    + r["concept_id"]
                    + " "
                    + band
                )
            path = ROOT / entry["file"]["path"]
            if sha256(path) != entry["file"]["sha256"]:
                raise ValueError("Input checksum mismatch")
            paths[r["granule_id"]][band] = str(path)
        p = paths[r["granule_id"]]
        with rasterio.open(p["mask"]) as ds:
            mask = ds.read(1, masked=True)
            codes = np.unique(mask.compressed()).tolist()
            if not set(codes).issubset({0, 1, 2, 3, 4, 5, 255}):
                raise ValueError("Unknown GCOV mask code")
            description = ds.tags(1).get("description", "")
            if not all(t in description.lower() for t in ["subswath", "255", "0"]):
                raise ValueError("Mask semantics not confirmed in actual science file")
        for pol in ["HHHH", "HVHV"]:
            with rasterio.open(p[pol]) as ds:
                tags = ds.tags(1)
                if tags.get("units") != "1" or pol not in tags.get("long_name", ""):
                    raise ValueError("Unexpected power metadata")
            layer = read_cogs(p[pol], p["mask"], p["numberOfLooks"], MASK_CONVENTION)
            if (
                layer.crs.to_epsg() != 32754
                or abs(layer.transform.a) != 20
                or abs(layer.transform.e) != 20
            ):
                raise ValueError("Unexpected NISAR grid")
            qa.append(
                dict(
                    granule_id=r["granule_id"],
                    polarization=pol,
                    mask_codes=codes,
                    valid_pixels=int(layer.valid.sum()),
                    valid_fraction=float(layer.valid.mean()),
                    median_db=float(
                        np.nanmedian(
                            power_db(np.where(layer.valid, layer.power, np.nan))
                        )
                    ),
                )
            )
    for other in records[1:]:
        for pol in ["HHHH", "HVHV"]:
            cfg = {"polarization": pol, "mask_convention": MASK_CONVENTION}
            for key, r in [("before", records[0]), ("after", other)]:
                p = paths[r["granule_id"]]
                cfg[key] = dict(
                    granule_id=r["granule_id"],
                    power=p[pol],
                    mask=p["mask"],
                    looks=p["numberOfLooks"],
                )
            name = records[0]["start"][:10] + "_" + other["start"][:10] + "_" + pol
            config = out / (name + ".json")
            config.write_text(json.dumps(cfg, indent=2))
            if not (out / name / "result.json").exists():
                run(config, out / name)
            result_path = out / name / "result.json"
            result = json.loads(result_path.read_text())
            if result["configuration"] != cfg:
                raise ValueError(
                    "Existing result configuration differs; use a new output directory"
                )
            result["source_identity"] = (
                "Input hashes and layer identities verified against recorded Harmony jobs and revalidated CMR granules by analyze_real"
            )
            result_path.write_text(json.dumps(result, indent=2))
    # Primary comparison ends September 28/29; October serves as a third radar epoch.
    projected = {}
    for i, r in enumerate(records[:2]):
        p = paths[r["granule_id"]]
        for pol in ["HHHH", "HVHV"]:
            l = read_cogs(p[pol], p["mask"], p["numberOfLooks"], MASK_CONVENTION)
            a = np.where(l.valid, l.power, np.nan).astype("float32")
            dest = np.full(SHAPE, np.nan, dtype="float32")
            reproject(
                a,
                dest,
                src_transform=l.transform,
                src_crs=l.crs,
                src_nodata=np.nan,
                dst_transform=TRANSFORM,
                dst_crs=CRS,
                dst_nodata=np.nan,
                resampling=Resampling.average,
            )
            projected[f"n{i}_{pol}"] = dest
    for i, date in enumerate(["20260821", "20260926"]):
        for band in ["vv", "vh"]:
            with rasterio.open(
                ROOT / f"outputs/comparison/sentinel1rtc_{date}_{band}.tif"
            ) as ds:
                projected[f"s{i}_{band}"] = ds.read(1)
    h, w = (SHAPE[0] // 5) * 5, (SHAPE[1] // 5) * 5
    common = np.logical_and.reduce(
        [np.isfinite(a) & (a > 0) for a in projected.values()]
    )[:h, :w]
    blocks = {}
    coverage = None
    for k, a in projected.items():
        blocks[k], coverage = block_power(a[:h, :w], common, 5)
    keep = coverage >= 0.8
    delta = {}
    for pol in ["HHHH", "HVHV"]:
        delta[pol] = np.where(
            keep, power_db(blocks["n1_" + pol]) - power_db(blocks["n0_" + pol]), np.nan
        )
    for pol in ["vv", "vh"]:
        delta[pol] = np.where(
            keep, power_db(blocks["s1_" + pol]) - power_db(blocks["s0_" + pol]), np.nan
        )
    delta["HH_minus_HV"] = delta["HHHH"] - delta["HVHV"]
    for key, array in delta.items():
        with rasterio.open(
            out / ("matched100m_" + key + "_change_db.tif"),
            "w",
            driver="COG",
            height=array.shape[0],
            width=array.shape[1],
            count=1,
            dtype="float32",
            crs=CRS,
            transform=TRANSFORM * rasterio.Affine.scale(5),
            nodata=np.nan,
            compress="DEFLATE",
        ) as ds:
            ds.write(array.astype("float32"), 1)
            ds.set_band_description(1, "Measured change dB; not flood classification")

    def fraction(a):
        return a[:h, :w].reshape(h // 5, 5, w // 5, 5).mean(axis=(1, 3))

    with rasterio.open(ROOT / "data/raw/comparison/worldcover_2021.tif") as ds:
        lc = ds.read(1)
    tree_fraction = fraction(lc == 10)
    tree = tree_fraction >= 0.6
    crop = fraction(lc == 40) >= 0.6
    optical = []
    for date in ["20260823", "20260929"]:
        with rasterio.open(ROOT / f"outputs/comparison/sentinel2_{date}_scl.tif") as ds:
            optical.append(ds.read(1))
    optical_nonwater = (fraction(np.isin(optical[0], [4, 5])) >= 0.8) & (
        fraction(np.isin(optical[1], [4, 5])) >= 0.8
    )

    def summarize(mask):
        result = {"blocks": int((mask & keep).sum())}
        for k, a in delta.items():
            values = a[mask & keep]
            values = values[np.isfinite(values)]
            result[k] = {
                "median_db": float(np.median(values)) if values.size else None,
                "q25_q75_db": np.percentile(values, [25, 75]).tolist()
                if values.size
                else None,
            }
        return result

    groups = {
        "all": summarize(keep),
        "tree_cover_2021": summarize(tree),
        "cropland_2021": summarize(crop),
        "tree_optical_nonwater": summarize(tree & optical_nonwater),
    }
    eligible = (
        tree
        & optical_nonwater
        & keep
        & (delta["HHHH"] > 0)
        & (delta["HH_minus_HV"] > 0)
    )
    flat = np.flatnonzero(eligible)
    ranked = flat[np.argsort(delta["HH_minus_HV"].ravel()[flat])[::-1]][:20]
    to_geo = Transformer.from_crs(CRS, 4326, always_xy=True)
    features = []
    for index in ranked:
        row, col = np.unravel_index(index, eligible.shape)
        x, y = TRANSFORM * (col * 5 + 2.5, row * 5 + 2.5)
        lon, lat = to_geo.transform(x, y)
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "status": "HYPOTHESIS",
                    "interpretation": "Exploratory co-pol-relative increase, not a flood detection",
                    **{k: float(a[row, col]) for k, a in delta.items()},
                    "joint_valid_fraction": float(coverage[row, col]),
                    "tree_cover_fraction_2021": float(tree_fraction[row, col]),
                },
            }
        )
    (out / "candidate_investigation_points.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, indent=2)
    )
    report = {
        "measurement_status": "VERIFIED: actual calibrated raster files processed; interpretation unvalidated",
        "hypothesis_outcome": "INCONCLUSIVE — complementary radar response can be measured, but improved flood detection or oxygen prediction has not been independently tested",
        "qa": qa,
        "groups_100m": groups,
        "nisar_dates": [r["start"] for r in records],
        "comparison_dates": {
            "sentinel1": ["2026-08-21", "2026-09-26"],
            "sentinel2": ["2026-08-23", "2026-09-29"],
        },
        "candidate_count": len(features),
        "eligible_blocks": int(eligible.sum()),
        "independent_reference": "DEW watering report and downloaded local channel water-level/oxygen observations; see independent_observations.json. Neither provides pixel inundation labels.",
        "accuracy_metrics": None,
        "oxygen_prediction": None,
        "limitations": [
            "No independent geolocated subcanopy labels",
            "Different orbit geometry, polarization and frequency across sensors",
            "Dates differ by up to two days in primary comparison",
            "2021 land cover may not represent 2026 vegetation; tree class is not a dense-canopy map",
            "100m blocks are averages of 20m power, not native sensor resolution",
            "No local cross-sensor radiometric calibration",
            "Candidate ranking is exploratory selection, not calibrated probability",
            "Study rectangle includes land beyond the named floodplains",
            "August is a comparison baseline, not a verified dry or pre-watering state",
            "Provisional P05023 products: residual RFI/ripples and local calibration errors remain possible",
            "Subswath mask and looks verified; inputDataExceptionMask not exposed by this Harmony collection",
            "Grid alignment verified; independent subpixel co-registration accuracy not measured",
        ],
    }
    (out / "science_result.json").write_text(json.dumps(report, indent=2))
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    extent = [
        left := TRANSFORM.c / 1000,
        (TRANSFORM.c + w * 20) / 1000,
        (TRANSFORM.f - h * 20) / 1000,
        TRANSFORM.f / 1000,
    ]
    for ax, (key, title) in zip(
        axes.flat,
        [
            ("HHHH", "NISAR HH change"),
            ("HVHV", "NISAR HV change"),
            ("vv", "Sentinel-1 VV change"),
            ("HH_minus_HV", "NISAR change in HH/HV ratio"),
        ],
    ):
        im = ax.imshow(delta[key], extent=extent, cmap="RdBu_r", vmin=-5, vmax=5)
        ax.set_title(title)
        ax.set_xlabel("UTM 54S easting (km)")
        ax.set_ylabel("Northing (km)")
        fig.colorbar(im, ax=ax, label="dB")
    fig.suptitle(
        "Observed radar changes — late August to late September 2026\n100 m power averages; environmental cause and sensor advantage unvalidated",
        fontsize=13,
    )
    fig.tight_layout()
    fig.savefig(out / "radar_comparison.png", dpi=160)
    plt.close(fig)
    # Small actual-data geographic mesh for a clearly labeled 3D signal display.
    sampled = delta["HHHH"][::4, ::4]
    mesh = {
        "values": np.where(np.isfinite(sampled), sampled, 0).round(3).tolist(),
        "valid": np.isfinite(sampled).tolist(),
        "units": "dB",
        "spacing_m": 400,
        "origin_utm": [TRANSFORM.c, TRANSFORM.f],
        "label": "Vertical axis is radar change, NOT terrain or water depth",
    }
    mesh["layers"] = {
        k: np.where(np.isfinite(a[::4, ::4]), a[::4, ::4], 0).round(3).tolist()
        for k, a in delta.items()
    }
    mesh["sample_centers_origin_utm"] = [TRANSFORM.c + 50, TRANSFORM.f - 50]
    (out / "signal_mesh.json").write_text(json.dumps(mesh))
    print(
        json.dumps(
            {"qa": qa, "groups": groups, "candidate_count": len(features)}, indent=2
        )
    )


if __name__ == "__main__":
    main()
