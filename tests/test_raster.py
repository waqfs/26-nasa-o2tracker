import h5py
import numpy as np
import pytest
from pyproj import CRS
from rasterio.transform import Affine
from canopy_pulse.raster import (
    Layer,
    read_hdf5,
    aligned,
    write_cog,
    read_cogs,
    MASK_CONVENTION,
)


@pytest.fixture
def fixture_hdf(tmp_path):
    p = tmp_path / "synthetic.h5"
    with h5py.File(p, "w") as f:
        g = f.create_group("/science/LSAR/GCOV/grids/frequencyA")
        g["HHHH"] = np.array([[1.0, 10.0], [0.0, -1.0]])
        g["mask"] = np.array([[1, 1], [255, 0]], dtype="uint8")
        g["mask"].attrs["description"] = "subswath mask: 0 invalid, 255 fill"
        g["numberOfLooks"] = np.ones((2, 2)) * 4
        g["xCoordinates"] = [500010.0, 500030.0]
        g["yCoordinates"] = [6200010.0, 6199990.0]
        g["projection"] = 32754
    return p


def test_hdf_structure_and_transform(fixture_hdf):
    l = read_hdf5(fixture_hdf)
    assert l.transform == Affine(20, 0, 500000, 0, -20, 6200020)
    assert l.valid.sum() == 2 and l.crs == CRS.from_epsg(32754)


def test_unknown_mask_rejected(fixture_hdf):
    with h5py.File(fixture_hdf, "r+") as f:
        f["/science/LSAR/GCOV/grids/frequencyA/mask"].attrs["description"] = "unknown"
    with pytest.raises(ValueError):
        read_hdf5(fixture_hdf)


def test_missing_hdf(tmp_path):
    p = tmp_path / "empty.h5"
    with h5py.File(p, "w"):
        pass
    with pytest.raises(KeyError):
        read_hdf5(p)


def test_alignment_rejects_half_pixel(fixture_hdf):
    a = read_hdf5(fixture_hdf)
    b = read_hdf5(fixture_hdf)
    b.transform = b.transform * Affine.translation(0.5, 0)
    with pytest.raises(ValueError):
        aligned(a, b)


def test_cog_roundtrip(fixture_hdf, tmp_path):
    a = read_hdf5(fixture_hdf)
    for key in ("power", "mask", "looks"):
        write_cog(tmp_path / f"{key}.tif", getattr(a, key), a, key)
    b = read_cogs(
        *(tmp_path / f"{key}.tif" for key in ("power", "mask", "looks")),
        MASK_CONVENTION,
    )
    aligned(a, b)
    np.testing.assert_array_equal(a.valid, b.valid)
