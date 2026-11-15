"""Sensor ablation, temporal evidence gating and absence of invented physical constraints."""

import json
from dataclasses import replace
import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from oxygen_debt.essentiality import dossier, numeric_delta, digest
from oxygen_debt.investigation import timestamp
from oxygen_debt.settings import read_json, PROJECT_ROOT
from oxygen_debt.flood import experiment, FloodExperiment


def test_ablation_evidence_arms_change_measurements_without_constraints():
    a, b, c = [dossier(arm=k) for k in ["A", "B", "C"]]
    assert a["field"] == b["field"] == c["field"]
    assert a["fixed_anchor_utc"] == b["fixed_anchor_utc"] == c["fixed_anchor_utc"]
    assert not a["conventional"] and not a["nisar"]
    assert b["conventional"] and not b["nisar"]
    assert c["nisar"] and c["diagnostic"]
    assert b["conventional"] == c["conventional"]
    for d in [a, b, c]:
        assert d["quantitative_flood_constraint"] is None
        assert d["constrained_oxygen_parameters"] == []
        assert not d["oxygen_uncertainty_reduction_demonstrated"]
        assert "not a sensor-blind" in d["selection_caution"]


def test_recorded_cutoff_excludes_future_optical_observations():
    d = dossier(pass_index=1)
    assert not any(x["date"] == "20260929" for x in d["conventional"]["optical"])
    for values in d["conventional"].values():
        for row in values:
            assert all(
                timestamp(t) <= timestamp(d["fixed_anchor_utc"])
                for t in row["observation_times"]
            )
    assert all(
        timestamp(v[0]) <= timestamp(d["fixed_anchor_utc"])
        for v in d["field"]["visits"]
    )
    assert not dossier(pass_index=0)["diagnostic"]


def test_offset_sensitivity_is_arithmetic_not_a_flood_estimate():
    d = dossier()
    x = d["diagnostic"]
    for name, offset in x["assumed_reference_offsets_db"].items():
        assert x["local_hh_residuals_under_assumed_offsets_db"][name] == pytest.approx(
            x["hh_change_db"] - offset
        )
    assert x["hh_minus_hv_change_db"] == pytest.approx(
        x["hh_change_db"] - x["hv_change_db"]
    )
    assert "not calibrated uncertainty bounds" in x["interpretation"]
    assert d["measurement_plan"][0]["where"]["latitude"] == d["latitude"]
    assert "no optimal placement" in d["measurement_plan"][0]["basis"]


def test_frozen_independent_ablation_hashes_are_identical_and_current():
    protocol = read_json("provenance/essentiality_protocol.json")
    prefix = (
        (PROJECT_ROOT / "docs/NISAR_ESSENTIALITY.md")
        .read_text(encoding="utf-8")
        .split("\n\n## Executed ablation result")[0]
    )
    import hashlib

    assert (
        hashlib.sha256(prefix.encode()).hexdigest()
        == protocol["initial_audit_prefix_normalized_lf_sha256"]
    )
    report = read_json("derived/nisar_ablation.json")
    assert [r["arm"] for r in report["arms"]] == ["A", "B", "C"]
    assert len({r["result_sha256"] for r in report["arms"]}) == 1
    assert all(
        r["max_absolute_numeric_output_difference_from_A"] == 0 for r in report["arms"]
    )
    control = report["matched_upstream_control"]
    assert len({r["result_sha256"] for r in control["arms"]}) == 1
    assert all(
        r["max_absolute_numeric_output_difference_from_A"] == 0 for r in control["arms"]
    )
    assert all(
        v["observation"]["grade"] == "GOOD" for v in control["boundary_inputs"].values()
    )
    saved = read_json("derived/flood_experiment.json")["default"]
    assert report["arms"][0]["result_sha256"] == digest(saved)
    assert digest({"x": 100}) == digest({"x": 100.0})
    assert digest({"x": 1.0}) != digest({"x": 1.0000000001})
    changed = dict(saved, seed=saved["seed"] + 1)
    assert digest(changed) != digest(saved)
    assert numeric_delta({"x": [1.0, 3.0]}, {"x": [1.0, 4.0]}) == 1
    with pytest.raises(ValueError):
        numeric_delta({"x": [1.0]}, {"x": [1.0, 2.0]})


def test_live_backend_arms_preserve_outputs_and_hide_removed_observables():
    client = TestClient(app)
    results = []
    for arm in ["A", "B", "C"]:
        response = client.post(
            "/api/flood-experiment", json={"evidence_arm": arm, "area_ha": 140}
        )
        assert response.status_code == 200
        d = response.json()
        results.append(d)
        assert d["evidence_arm"] == arm and d["nisar_constrained_parameters"] == []
        assert d["measured_target_oxygen_used"] is False
    assert len({r["model_output_sha256"] for r in results}) == 1
    assert results[0]["river_oxygen_quantiles"] == results[2]["river_oxygen_quantiles"]
    default = client.post("/api/flood-experiment", json={}).json()
    assert (
        default["model_output_sha256"]
        == read_json("derived/nisar_ablation.json")["arms"][0]["result_sha256"]
    )
    a = client.get("/api/essentiality?arm=A").json()
    assert not a["nisar"] and not a["conventional"]
    assert client.get("/api/essentiality?arm=unknown").status_code == 422
    assert client.get("/api/essentiality?location=unknown").status_code == 404
    assert client.get("/api/ablation").status_code == 200
    revealed = client.get("/api/flood-reveal?evidence_arm=B").json()
    assert (
        "radar_db" not in revealed["selected"]
        and "granule_id" not in revealed["selected"]
    )


def test_all_member_model_audit_discloses_coverage_and_passes_declared_metric():
    report = read_json("derived/model_audit_03.json")
    assert len(report["scenarios"]) == 3
    for row in report["scenarios"]:
        assert row["members"] == 512
        assert row["maximum_carbon_ledger_residual_kg"] < 1e-5
        assert row["maximum_oxygen_ledger_residual_kg"] < 1e-5
        assert row["max_minimum_river_difference_mg_l"] <= 0.005
        assert row["water_boundary_continuity_residual_m3_day"] < 1e-6
    assert report["stoichiometry_kg_O2_per_kg_C"] == 32 / 12
