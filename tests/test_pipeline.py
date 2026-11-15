import json
import h5py
import numpy as np
from pathlib import Path
from canopy_pulse.process import run


def test_end_to_end_synthetic_pipeline(tmp_path):
    """Synthetic regression, never environmental validation."""
    selected = json.loads(
        (
            Path(__file__).resolve().parents[1] / "data/provenance/selected.json"
        ).read_text()
    )
    cfg = {"polarization": "HHHH"}
    for label, record, value in [
        ("before", selected[0], 1.0),
        ("after", selected[-1], 10.0),
    ]:
        p = tmp_path / f"{label}.h5"
        with h5py.File(p, "w") as f:
            ident = f.create_group("/science/LSAR/identification")
            for dataset, key in {
                "granuleId": "granule_id",
                "trackNumber": "track",
                "frameNumber": "frame",
                "orbitPassDirection": "direction",
                "compositeReleaseId": "crid",
                "productVersion": "product_version",
            }.items():
                ident[dataset] = record[key]
            g = f.create_group("/science/LSAR/GCOV/grids/frequencyA")
            g["HHHH"] = np.full((2, 2), value)
            g["mask"] = np.array([[1, 1], [1, 255]], dtype="uint8")
            g["mask"].attrs["description"] = "subswath 0 invalid 255 fill"
            g["numberOfLooks"] = np.ones((2, 2)) * 4
            g["xCoordinates"] = [500010.0, 500030.0]
            g["yCoordinates"] = [6200010.0, 6199990.0]
            g["projection"] = 32754
        cfg[label] = {"granule_id": record["granule_id"], "hdf5": str(p)}
    config = tmp_path / "config.json"
    config.write_text(json.dumps(cfg))
    report = run(config, tmp_path / "out")
    assert report["median_change_db"] == 10
    assert report["joint_valid_pixels"] == 3
    assert report["flood_area"] is None and report["oxygen_prediction"] is None
    assert (tmp_path / "out/change_db.tif").exists()
    assert (tmp_path / "out/change_preview.png").exists()
    assert len(report["inputs"]) == 2
