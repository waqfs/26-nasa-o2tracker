"""Independent dimensional, conservation, limiting-case and disclosure checks."""

import hashlib, json
from dataclasses import replace
import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from oxygen_debt.flood import (
    FloodExperiment,
    parameter_bounds,
    integrate,
    experiment,
    RATIO,
)
from oxygen_debt.settings import read_json, SNAPSHOT_ROOT
from oxygen_debt.flood_context import context, reveal


def parameters(**changes):
    config = FloodExperiment(hydrology_spread=0, temperature_c=20)
    p = {k: np.array([(v[0] + v[1]) / 2]) for k, v in parameter_bounds(config).items()}
    p.update({k: np.array([v], dtype=float) for k, v in changes.items()})
    return p


def test_carbon_units_finite_release_and_stoichiometry():
    p = parameters(
        area_ha=1,
        litter_fast_g_m2=100,
        litter_slow_g_m2=0,
        yield_fast_mg_g=100,
        release_fast_per_day=0.5,
        decay_per_day=0,
        exchange_per_day=0,
        reaeration_per_day=0,
    )
    r = integrate(p, days=2)
    # 100 g/m2 * 10,000 m2 * 100 mg C/g = 100 kg C; no new carbon after initial wetting.
    np.testing.assert_allclose(r["initial_carbon_kg"], 100)
    np.testing.assert_allclose(r["potential_oxygen_kg"], 100 * 32 / 12)
    np.testing.assert_allclose(r["unreleased_carbon_kg"], 100 * np.exp(-1), rtol=1e-12)
    np.testing.assert_allclose(
        r["dissolved_carbon_kg"], 100 * (1 - np.exp(-1)), rtol=1e-12
    )
    np.testing.assert_allclose(r["consumed_oxygen_kg"], 0)


def test_closed_floodplain_cannot_consume_more_oxygen_than_available():
    p = parameters(
        area_ha=10,
        depth_m=0.2,
        exchange_per_day=0,
        reaeration_per_day=0,
        litter_fast_g_m2=1000,
        litter_slow_g_m2=3000,
    )
    r = integrate(p, days=14, upstream=9)
    oxygen_inventory = 10 * 10000 * 0.2 * 9 / 1000
    assert r["consumed_oxygen_kg"][0] <= oxygen_inventory + 1e-8
    assert r["minimum_fp"][0] >= -1e-10
    np.testing.assert_allclose(
        r["carbon_remaining_kg"] + r["consumed_oxygen_kg"] / RATIO,
        r["initial_carbon_kg"],
        atol=1e-7,
    )
    assert r["carbon_remaining_kg"][0] > 0


def test_disconnected_floodplain_has_no_downstream_carbon_effect():
    p = parameters(connected_fraction=0, reaeration_per_day=0)
    r = integrate(p, days=4, upstream=9)
    np.testing.assert_allclose(r["minimum"], 9, atol=1e-10)
    assert r["minimum_fp"][0] < 9
    np.testing.assert_allclose(
        r["carbon_remaining_kg"],
        r["initial_carbon_kg"]
        + r["carbon_boundary_net_kg"]
        - r["consumed_oxygen_kg"] / RATIO,
        atol=1e-7,
    )


def test_zero_litter_and_equal_advection_rates_are_finite():
    p = parameters(
        litter_fast_g_m2=0,
        litter_slow_g_m2=0,
        reaeration_per_day=0,
        exchange_per_day=0.1,
        connected_fraction=0,
        river_flow_m3_s=0.1 * 5000 * 1000 / 86400,
    )
    r = integrate(p, days=3)
    np.testing.assert_allclose(r["minimum"], 9, atol=1e-10)
    assert r["oxygen_balance_error_kg"] < 1e-6
    assert r["carbon_balance_error_kg"] < 1e-6


def test_oxygen_and_carbon_ledgers_and_time_refinement():
    p = parameters(
        litter_fast_g_m2=250,
        litter_slow_g_m2=800,
        river_flow_m3_s=30,
        connected_fraction=0.8,
    )
    a = integrate(p, days=14, dt=0.025)
    b = integrate(p, days=14, dt=0.0125)
    assert a["oxygen_balance_error_kg"] < 1e-6 and a["carbon_balance_error_kg"] < 1e-6
    np.testing.assert_allclose(a["minimum"], b["minimum"], atol=0.003)
    assert a["carbon_boundary_net_kg"][0] < 0


def test_reproducible_ensemble_and_output_specific_sensitivity():
    config = FloodExperiment(samples=64, seed=25)
    a = experiment(config)
    b = experiment(config)
    assert a == b
    assert a["ensemble_members"] == 128 and not a["measurement_used_for_fit"]
    assert len(a["river_oxygen_quantiles"]) == 3
    assert all(v >= 0 for v in a["minimum_river_oxygen_mg_l"])
    assert a["oxygen_balance_error_kg"] < 1e-5
    potential = {
        x["parameter"]: x for x in a["sensitivity"]["potential_oxygen_demand_kg"]
    }
    assert potential["river_flow_m3_s"]["total_order"] == 0
    assert potential["release_fast_per_day"]["total_order"] == 0
    assert potential["litter_fast_g_m2"]["total_order"] > 0
    with pytest.raises(ValueError):
        parameter_bounds(replace(config, depth_m=0))
    with pytest.raises(ValueError):
        parameter_bounds(replace(config, temperature_c=30))
    with pytest.raises(ValueError):
        parameter_bounds(replace(config, area_ha=float("nan")))


def test_input_provenance_quality_and_temporal_reveal():
    for item in read_json("provenance/flood_context_manifest.json")[
        "entries"
    ] + read_json("provenance/field_visit_manifest.json"):
        assert (
            hashlib.sha256((SNAPSHOT_ROOT / item["file"]).read_bytes()).hexdigest()
            == item["sha256"]
        )
    c = context("A4261108", "candidate-2", 1)
    assert c["boundary_inputs"]["oxygen"]["station"] == "A4261024"
    assert c["boundary_inputs"]["oxygen"]["observation"] is None
    assert c["boundary_inputs"]["oxygen"]["excluded_grades"] == ["UNVERIFIED TELEM"]
    upstream = context("A4261053", "candidate-2", 0)["boundary_inputs"]["oxygen"]
    assert upstream["observation"]["grade"] == "GOOD"
    assert abs(upstream["offset_hours"]) <= 12
    assert "UNSUPPORTED" in c["quantitative_inundation_verdict"]
    assert reveal("A4261108", "candidate-2", 1, "as_of")["observations"] == []
    assert reveal("A4261108", "candidate-2", 1)["selected"][
        "ground_mean"
    ] == pytest.approx(9.281215277777778, abs=0.001)


def test_api_no_target_fitting_and_explicit_outcome_reveal(monkeypatch):
    import oxygen_debt.flood_context as module

    original = module.read_json

    def guarded(path):
        if path == "derived/stations.json":
            raise AssertionError("Target oxygen used before reveal")
        return original(path)

    monkeypatch.setattr(module, "read_json", guarded)
    client = TestClient(app)
    assert (
        client.post(
            "/api/flood-experiment", json={"use_boundary_measurements": True}
        ).status_code
        == 422
    )
    response = client.post(
        "/api/flood-experiment",
        json={
            "use_boundary_measurements": True,
            "station": "A4261053",
            "pass_index": 0,
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert not result["measured_target_oxygen_used"] and result["boundary_context"]
    assert result["configuration"]["temperature_c"] is not None
    assert client.post("/api/flood-experiment", json={"depth_m": 0}).status_code == 422
    assert client.get("/api/flood-evidence?location=unknown").status_code == 404
    assert client.get("/api/flood-evidence?pass_index=9").status_code == 422
    json.dumps(result, allow_nan=False)
