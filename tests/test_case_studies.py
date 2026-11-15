"""Regression tests for the case-study data used by the O2tracker Evidence and Context views."""

import json, math, re
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import app

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data/derived/case_studies.json").read_text(encoding="utf-8"))
A, B = DATA["everglades_e15"], DATA["maurepas_low_oxygen"]
client = TestClient(app)


def rmse(rows, key):
    return math.sqrt(sum((r[key] - r["observed_cm"]) ** 2 for r in rows) / len(rows))


def test_headline_numbers_recompute_from_rows():
    rows = A["rows"]
    assert len(rows) == A["n_folds"] == 33
    assert abs(rmse(rows, "nisar_cm") - 2.31) < 0.02
    assert abs(rmse(rows, "multiquadric_cm") - 3.43) < 0.02
    assert (
        round(A["pooled_rmse_cm"]["nisar"], 2) == 2.31
        and round(A["pooled_rmse_cm"]["multiquadric_strongest_baseline"], 2) == 3.43
    )
    best_base = min(
        ["multiquadric_cm", "idw_cm", "thin_plate_cm", "nearest_cm"],
        key=lambda k: rmse(rows, k),
    )
    assert best_base == "multiquadric_cm"
    assert (
        abs(
            A["relative_rmse_reduction_percent"]
            - 100 * (1 - rmse(rows, "nisar_cm") / rmse(rows, "multiquadric_cm"))
        )
        < 0.6
    )
    for pair, v in A["per_pair_rmse_cm"].items():
        sub = [r for r in rows if r["pair"] == pair]
        assert (
            abs(rmse(sub, "nisar_cm") - v["nisar"]) < 0.02
            and abs(rmse(sub, "multiquadric_cm") - v["multiquadric"]) < 0.02
        )


def test_scope_and_limitations_are_explicit():
    text = " ".join(A["limitations"]).lower()
    for phrase in [
        "exploratory",
        "single-geometry",
        "not a fully replicated",
        "proxy",
        "not demonstrate oxygen prediction",
        "discharge",
        "residence time",
    ]:
        assert phrase in text
    assert "INCONCLUSIVE" in A["replication_descending_stack_170"]
    assert A["eligibility_pairs_passed"] == 3 and A["eligibility_pairs_total"] == 8
    assert (
        A["gauge_boot95_mean_abs_improvement_cm"][0] < 0
    )  # gauge-level interval includes zero and is disclosed


def test_placebo_does_not_reproduce_improvement():
    for pair, v in A["shuffled_phase_control"].items():
        assert v["placebo_mean_rmse_cm"] > A["per_pair_rmse_cm"][pair]["multiquadric"]
        assert v["fraction_placebo_as_good_as_nisar"] < 0.01


def test_sites_are_geographically_separate_and_oxygen_values_exact():
    for r in A["rows"]:
        assert 25 < r["lat"] < 27 and -81.5 < r["lon"] < -80
    for p in B["profiles"]:
        assert (
            29.5 < p["lat"] < 31
            and -91 < p["lon"] < -90
            and p["time_local"].startswith("2026")
        )
    low = min(B["profiles"], key=lambda p: p["do_min_mg_l"])
    assert (low["station"], low["time_local"][:10], low["do_min_mg_l"]) == (
        "SWMP0204",
        "2026-06-01",
        0.89,
    )
    june = {
        p["station"]
        for p in B["profiles"]
        if p["time_local"].startswith("2026-06-01") and p["do_min_mg_l"] < 2
    }
    assert june == {"SWMP0202", "SWMP0203", "SWMP0204", "SWMP0205"}
    assert (
        "no causal" in B["no_causal_link"].lower()
        and "different sites" in B["no_causal_link"].lower()
    )


def test_routes():
    h = client.get("/api/health").json()
    assert h["product"] == "O2tracker" and h["release"] == "0.4.0-rc1"
    assert (
        client.get("/api/case-studies").json()["schema"] == "oxygen-debt/case-studies/1"
    )  # historical schema id kept for provenance
    r = client.get("/case-studies", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/app#evidence"


def test_provenance_hashes_present():
    for k, v in DATA["provenance"].items():
        assert re.fullmatch(r"[0-9a-f]{64}", v), k
