"""Run: python -m canopy_pulse.process pair.json --output outputs/run-name"""

import argparse, json
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .science import assert_compatible, change, power_db
from .raster import (
    read_cogs,
    read_hdf5,
    aligned,
    write_cog,
    sha256,
    verify_hdf_identity,
)


def run(config, output):
    cfg = json.loads(Path(config).read_text())
    from oxygen_debt.settings import PROJECT_ROOT, DATA_ROOT

    inventory_path = DATA_ROOT / "inventory.json"
    if not inventory_path.exists():
        inventory_path = PROJECT_ROOT / "data/provenance/inventory.json"
    inventory = {
        x["granule_id"]: x
        for x in json.loads(inventory_path.read_text(encoding="utf-8"))
    }
    before, after = cfg["before"], cfg["after"]
    assert_compatible(inventory[before["granule_id"]], inventory[after["granule_id"]])

    def load(spec):
        if "hdf5" in spec:
            verify_hdf_identity(spec["hdf5"], inventory[spec["granule_id"]])
            return read_hdf5(
                spec["hdf5"], cfg.get("polarization", "HHHH"), bbox=cfg.get("bbox")
            )
        return read_cogs(
            spec["power"], spec["mask"], spec["looks"], cfg["mask_convention"]
        )

    a, b = load(before), load(after)
    aligned(a, b)
    d = change(a.power, b.power, a.valid, b.valid)
    if not np.isfinite(d).any():
        raise ValueError("No jointly valid pixels")
    out = Path(output)
    if out.exists() and any(out.iterdir()):
        raise ValueError("Use an empty output directory to preserve previous runs")
    out.mkdir(parents=True, exist_ok=True)
    write_cog(
        out / "change_db.tif",
        d,
        a,
        "Observed backscatter change dB; not flood classification",
    )
    for name, layer in [("before", a), ("after", b)]:
        write_cog(
            out / f"{name}_power.tif",
            np.where(layer.valid, layer.power, np.nan),
            layer,
            "Masked gamma0 linear power",
        )
    fig, ax = plt.subplots(figsize=(9, 6))
    lim = max(float(np.nanpercentile(np.abs(d), 98)), 0.01)
    im = ax.imshow(d, cmap="RdBu_r", vmin=-lim, vmax=lim)
    ax.set_title("NISAR backscatter change — cause unvalidated")
    ax.set_xlabel("Raster column")
    ax.set_ylabel("Raster row")
    fig.colorbar(im, ax=ax, label="dB")
    fig.tight_layout()
    fig.savefig(out / "change_preview.png", dpi=150)
    plt.close(fig)
    inputs = []
    for spec in (before, after):
        for key in ("power", "mask", "looks", "hdf5"):
            if key in spec:
                inputs.append(
                    dict(
                        path=spec[key],
                        sha256=sha256(spec[key]),
                        granule_id=spec["granule_id"],
                        layer=key,
                    )
                )
    report = dict(
        state="IMPLEMENTED BUT UNVALIDATED",
        interpretation="Measured radar change; environmental cause not independently validated",
        inputs=inputs,
        configuration=cfg,
        source_identity=(
            "Embedded HDF5 identifiers checked"
            if "hdf5" in before and "hdf5" in after
            else "COG mapping supplied by operator; verify against Harmony order metadata"
        ),
        joint_valid_pixels=int(np.isfinite(d).sum()),
        joint_valid_fraction=float(np.isfinite(d).mean()),
        median_change_db=float(np.nanmedian(d)),
        quantiles_db=np.nanpercentile(d, [5, 25, 50, 75, 95]).tolist(),
        flood_area=None,
        detection_accuracy=None,
        oxygen_prediction=None,
    )
    (out / "result.json").write_text(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.config, args.output), indent=2))
