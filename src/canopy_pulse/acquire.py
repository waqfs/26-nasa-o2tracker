"""Official Harmony acquisition. Credentials stay in memory; jobs resume from disk."""

import argparse, getpass, json, os, time, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlencode
import requests
import numpy as np
import rasterio
from shapely.geometry import Polygon, box
from harmony import Client, Request, Collection, BBox
from .science import assert_compatible
from .raster import sha256

import os

ROOT = Path(
    os.environ.get("OXYGEN_WORKSPACE_ROOT", Path(__file__).resolve().parents[2])
)
ACQ = ROOT / "data/acquisition"
COLLECTION = "C2854338529-ASF"
BBOX = [140.45, -34.55, 140.95, -34.15]
LAYERS = ["HHHH", "HVHV", "mask", "numberOfLooks"]


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def prepare():
    ACQ.mkdir(parents=True, exist_ok=True)
    caps = requests.get(
        "https://harmony.earthdata.nasa.gov/capabilities",
        params={"collectionId": COLLECTION},
        timeout=60,
    )
    caps.raise_for_status()
    caps = caps.json()
    save(ACQ / "capabilities.json", caps)
    variables = {
        v["name"].split("/")[-1]: v["href"].split("/")[-1]
        for v in caps["variables"]
        if v["name"].startswith("/science/LSAR/GCOV/grids/frequencyA/")
    }
    if not all(x in variables for x in LAYERS):
        raise ValueError("Required science/QA variables not supported")
    selected = json.loads(
        (
            ROOT / "data/selected.json"
            if (ROOT / "data/selected.json").exists()
            else ROOT / "data/provenance/selected.json"
        ).read_text()
    )
    # Three epochs bracket the reported September watering period; dry baseline remains unconfirmed.
    chosen = [
        r
        for r in selected
        if r["start"][:10] in ("2026-08-23", "2026-09-28", "2026-10-10")
    ]
    if len(chosen) != 3:
        raise ValueError("Expected epochs absent from selected inventory")
    audit = []
    for r in chosen:
        response = requests.get(
            "https://cmr.earthdata.nasa.gov/search/granules.umm_json",
            params={"concept_id": r["concept_id"]},
            timeout=60,
        )
        response.raise_for_status()
        body = response.json()
        save(ACQ / (r["concept_id"] + ".json"), body)
        if len(body["items"]) != 1:
            raise ValueError("Granule no longer resolves uniquely")
        u = body["items"][0]["umm"]
        attrs = {a["Name"]: a["Values"] for a in u["AdditionalAttributes"]}
        if u["GranuleUR"] != r["granule_id"]:
            raise ValueError("Granule identity changed")
        for key, attr in [
            ("track", "TRACK_NUMBER"),
            ("frame", "FRAME_NUMBER"),
            ("direction", "ASCENDING_DESCENDING"),
            ("bandwidth", "FREQUENCY_A_RANGE_BANDWIDTH"),
            ("product_version", "PRODUCT_VERSION"),
        ]:
            if r[key] != attrs[attr][0]:
                raise ValueError("Catalog metadata changed: " + key)
        if r["polarizations"] != attrs["FREQUENCY_A_POLARIZATION"]:
            raise ValueError("Polarizations changed")
        polygons = u["SpatialExtent"]["HorizontalSpatialDomain"]["Geometry"][
            "GPolygons"
        ]
        shapes = [
            Polygon([(p["Longitude"], p["Latitude"]) for p in v["Boundary"]["Points"]])
            for v in polygons
        ]
        from shapely.ops import unary_union

        extent = unary_union(shapes)
        aoi = box(*BBOX)
        coverage = extent.intersection(aoi).area / aoi.area
        audit.append(
            dict(
                granule_id=r["granule_id"],
                concept_id=r["concept_id"],
                aoi_catalog_coverage_fraction=coverage,
                record=r,
            )
        )
    for row in audit[1:]:
        assert_compatible(audit[0]["record"], row["record"])
    result = dict(
        checked_utc=datetime.now(timezone.utc).isoformat(),
        collection=COLLECTION,
        bbox=BBOX,
        variables={x: variables[x] for x in LAYERS},
        acquisitions=audit,
        rationale="Same track/frame/geometry, maturity, product version and dual polarization. Three epochs bracket reported September activity; pre-event dry state is not yet established. Catalog footprint is not pixel QA.",
    )
    save(ACQ / "request.json", result)
    print(
        "Verified",
        len(audit),
        "CMR identities; AOI coverage:",
        [round(x["aoi_catalog_coverage_fraction"], 4) for x in audit],
        flush=True,
    )
    return result


def probe_auth(request):
    row = request["acquisitions"][0]
    params = [
        ("granuleId", row["concept_id"]),
        ("subset", f"lon({BBOX[0]},{BBOX[2]})"),
        ("subset", f"lat({BBOX[1]},{BBOX[3]})"),
        ("format", "image/tiff"),
        ("forceAsync", "true"),
    ]
    url = f"https://harmony.earthdata.nasa.gov/{COLLECTION}/ogc-api-coverages/1.0.0/{request['variables']['HHHH']}/coverage/rangeset"
    r = requests.get(url, params=params, allow_redirects=False, timeout=60)
    result = dict(
        status=r.status_code,
        redirect_host=urlparse(r.headers.get("Location", "")).hostname,
        request_url=r.request.url,
        authenticated=False,
        checked_utc=datetime.now(timezone.utc).isoformat(),
    )
    save(ACQ / "access_probe.json", result)
    print(
        "Harmony access:",
        r.status_code,
        "redirect host:",
        result["redirect_host"],
        flush=True,
    )


def inspect(path):
    with rasterio.open(path) as ds:
        if ds.driver != "GTiff" or ds.crs is None or ds.count != 1:
            raise ValueError("Expected one-band georeferenced science GeoTIFF")
        a = ds.read(1, masked=True)
        v = a.compressed()
        v = v[np.isfinite(v)]
        return dict(
            path=str(path.relative_to(ROOT)),
            sha256=sha256(path),
            bytes=path.stat().st_size,
            crs=str(ds.crs),
            transform=list(ds.transform),
            shape=list(ds.shape),
            dtype=ds.dtypes[0],
            nodata=str(ds.nodata),
            valid_count=int(v.size),
            min=float(v.min()) if v.size else None,
            max=float(v.max()) if v.size else None,
            tags=ds.tags(),
            band_tags=ds.tags(1),
        )


def acquire(req, login=False):
    # Harmony-Py manages EDL authorization. Never print the client, exceptions or signed URLs.
    if login:
        username = input("Earthdata username (local console only): ")
        password = getpass.getpass("Earthdata password (hidden; never saved): ")
        client = Client(auth=(username, password), download_timeout=(30, 180))
        del password, username
    elif os.environ.get("EARTHDATA_TOKEN"):
        client = Client(token=os.environ["EARTHDATA_TOKEN"], download_timeout=(30, 180))
    else:
        client = Client(download_timeout=(30, 180))
    state_path = ACQ / "jobs.json"
    jobs = json.loads(state_path.read_text()) if state_path.exists() else {}
    for row in req["acquisitions"]:
        for layer, variable in req["variables"].items():
            key = row["concept_id"] + "_" + layer
            if key not in jobs:
                request = Request(
                    Collection(req["collection"]),
                    spatial=BBox(*req["bbox"]),
                    variables=[variable],
                    granule_id=[row["concept_id"]],
                    format="image/tiff",
                    max_results=1,
                    skip_preview=True,
                    ignore_errors=False,
                    labels=["canopy-pulse"],
                )
                job = client.submit(request)
                jid = job["jobID"] if isinstance(job, dict) else str(job)
                jobs[key] = dict(
                    job_id=jid,
                    granule_id=row["granule_id"],
                    layer=layer,
                    status="submitted",
                )
                save(state_path, jobs)
            entry = jobs[key]
            if entry.get("file") and (ROOT / entry["file"]["path"]).exists():
                if sha256(ROOT / entry["file"]["path"]) == entry["file"]["sha256"]:
                    continue
                raise ValueError("Existing downloaded file checksum mismatch")
            deadline = time.monotonic() + 3600
            while time.monotonic() < deadline:
                status = client.status(entry["job_id"])
                entry["status"] = status["status"]
                save(state_path, jobs)
                print(key, entry["status"], flush=True)
                if entry["status"] in ("successful", "complete"):
                    break
                if entry["status"] in ("failed", "canceled", "paused"):
                    raise RuntimeError(
                        "Harmony job did not complete; inspect job in Harmony portal"
                    )
                time.sleep(15)
            else:
                raise TimeoutError("Job retained for resume")
            urls = list(client.result_urls(entry["job_id"]))
            if len(urls) != 1:
                raise ValueError("Expected one result for a single granule/layer job")
            destination = ROOT / "data/raw" / row["granule_id"] / layer
            destination.mkdir(parents=True, exist_ok=True)
            downloaded = Path(
                client.download(
                    urls[0], directory=str(destination), overwrite=False
                ).result()
            )
            entry["file"] = inspect(downloaded)
            # Signed result URL is intentionally omitted. Job + exact request provide provenance.
            save(state_path, jobs)
    save(ACQ / "download_manifest.json", list(jobs.values()))
    save(
        ACQ / "status.json",
        dict(
            state="COMPLETE",
            verified_utc=datetime.now(timezone.utc).isoformat(),
            files=len(jobs),
            note="Previous access probes/errors are historical, not current blockers.",
        ),
    )
    print("All requested science layers downloaded and inspected.", flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--login", action="store_true")
    p.add_argument("--prepare-only", action="store_true")
    args = p.parse_args()
    req = prepare()
    if args.prepare_only:
        probe_auth(req)
        return
    try:
        acquire(req, args.login)
    except Exception as e:
        # Exception strings may contain credential-bearing URLs; retain only the exception class.
        save(
            ACQ / "last_error.json",
            dict(
                error_type=type(e).__name__,
                state="BLOCKED",
                time=datetime.now(timezone.utc).isoformat(),
            ),
        )
        print(
            "Acquisition stopped:",
            type(e).__name__,
            ". Credentials and signed URLs were not logged. Use --login in your local terminal if authentication is needed.",
            flush=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
