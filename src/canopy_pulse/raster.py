"""Read local calibrated products. Reject unknown masks and misaligned grids."""

from dataclasses import dataclass
from pathlib import Path
import hashlib
import h5py
import numpy as np
import rasterio
from rasterio.transform import Affine
from pyproj import CRS, Transformer
from .science import valid_pixels

MASK_CONVENTION = "gcov-subswath-0-invalid-255-fill"


@dataclass
class Layer:
    power: np.ndarray
    mask: np.ndarray
    looks: np.ndarray
    transform: Affine
    crs: CRS
    source: str

    @property
    def valid(self):
        return valid_pixels(self.power, self.mask, self.looks)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify_hdf_identity(path, record):
    fields = {
        "granuleId": "granule_id",
        "trackNumber": "track",
        "frameNumber": "frame",
        "orbitPassDirection": "direction",
        "compositeReleaseId": "crid",
        "productVersion": "product_version",
    }
    with h5py.File(path, "r") as f:
        group = f["/science/LSAR/identification"]
        for dataset, key in fields.items():
            value = group[dataset][()]
            if isinstance(value, bytes):
                value = value.decode()
            if str(value).upper() != str(record[key]).upper():
                raise ValueError(
                    f"Embedded HDF5 {dataset} disagrees with catalog identity"
                )


def aligned(a, b):
    if (
        a.crs != b.crs
        or a.power.shape != b.power.shape
        or not a.transform.almost_equals(b.transform, precision=1e-7)
    ):
        raise ValueError(
            "Grid mismatch; explicit documented power-domain resampling required"
        )


def read_cogs(power_path, mask_path, looks_path, mask_convention):
    if mask_convention != MASK_CONVENTION:
        raise ValueError(
            "GCOV mask convention must be explicitly confirmed from product specification"
        )
    arrays = []
    with rasterio.open(power_path) as p:
        transform, crs, shape = p.transform, p.crs, p.shape
        if crs is None:
            raise ValueError("Missing CRS")
    for path in (power_path, mask_path, looks_path):
        with rasterio.open(path) as ds:
            if (
                ds.crs != crs
                or ds.shape != shape
                or not transform.almost_equals(ds.transform)
            ):
                raise ValueError("Power/QA grid mismatch")
            arrays.append(ds.read(1, masked=True).astype(float).filled(np.nan))
    return Layer(*arrays, transform, CRS(crs), str(power_path))


def read_hdf5(path, polarization="HHHH", frequency="A", bbox=None):
    if polarization not in (
        "HHHH",
        "HVHV",
        "VVVV",
        "VHVH",
        "RHRH",
        "RVRV",
    ) or frequency not in ("A", "B"):
        raise ValueError("Only real diagonal power terms are supported")
    with h5py.File(path, "r") as f:
        g = f[f"/science/LSAR/GCOV/grids/frequency{frequency}"]
        description = g["mask"].attrs.get("description", "")
        if isinstance(description, bytes):
            description = description.decode()
        if not all(s in str(description).lower() for s in ("subswath", "255", "0")):
            raise ValueError(
                "Unrecognized mask description; inspect product before proceeding"
            )
        x, y = g["xCoordinates"][:], g["yCoordinates"][:]
        if len(x) < 2 or len(y) < 2:
            raise ValueError("Insufficient coordinate grid")
        dx, dy = float(x[1] - x[0]), float(y[1] - y[0])
        if (
            dx <= 0
            or dy >= 0
            or not np.allclose(np.diff(x), dx)
            or not np.allclose(np.diff(y), dy)
        ):
            raise ValueError("Expected regular north-up projected grid")
        crs = CRS.from_epsg(int(g["projection"][()]))
        if not crs.is_projected:
            raise ValueError("Projected grid required")
        r0, r1, c0, c1 = 0, len(y), 0, len(x)
        if bbox:
            west, south, east, north = Transformer.from_crs(
                4326, crs, always_xy=True
            ).transform_bounds(*bbox, densify_pts=21)
            cols = np.flatnonzero((x >= west) & (x <= east))
            rows = np.flatnonzero((y >= south) & (y <= north))
            if not len(cols) or not len(rows):
                raise ValueError("AOI does not intersect grid")
            c0, c1 = int(cols[0]), int(cols[-1] + 1)
            r0, r1 = int(rows[0]), int(rows[-1] + 1)
        window = np.s_[r0:r1, c0:c1]
        arrays = [g[name][window] for name in (polarization, "mask", "numberOfLooks")]
        transform = Affine(dx, 0, float(x[c0] - dx / 2), 0, dy, float(y[r0] - dy / 2))
        return Layer(*arrays, transform, crs, str(path))


def write_cog(path, array, layer, description):
    with rasterio.open(
        path,
        "w",
        driver="COG",
        height=array.shape[0],
        width=array.shape[1],
        count=1,
        dtype="float32",
        crs=layer.crs,
        transform=layer.transform,
        nodata=np.nan,
        compress="DEFLATE",
    ) as ds:
        ds.write(np.asarray(array, dtype="float32"), 1)
        ds.set_band_description(1, description)
