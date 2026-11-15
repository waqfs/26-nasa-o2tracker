from datetime import timezone
import json
import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend.app import app
from oxygen_debt.investigation import (
    compare,
    correlation_summary,
    timestamp,
    daily_covariates,
    load_data,
)
from oxygen_debt.models import Scenario, simulate, freshwater_equilibrium
from oxygen_debt.settings import SNAPSHOT_ROOT
from canopy_pulse.raster import sha256

client = TestClient(app)


def test_verified_source_hashes_quality_and_ranges():
    data, _ = load_data()
    expected = {
        "A4261108": (8.91782986111111, 10.737135416666666),
        "A4261053": (8.42201388888889, 11.148663194444444),
    }
    for station in data["stations"]:
        variable = station["variables"]["oxygen"]
        path = SNAPSHOT_ROOT.parent / variable["raw_file"]
        assert sha256(path) == variable["sha256"]
        rows = [
            r
            for r in variable["observations"]
            if r["grade"] == "GOOD" and r["value"] is not None
        ]
        assert len(rows) == 53
        np.testing.assert_allclose(
            [min(r["value"] for r in rows), max(r["value"] for r in rows)],
            expected[station["id"]],
        )
        assert len(variable["observations"]) == 54


def test_timezone_and_actual_alignment():
    assert (
        timestamp("2026-08-24T00:00:00+09:30").isoformat()
        == "2026-08-23T14:30:00+00:00"
    )
    with pytest.raises(ValueError):
        timestamp("2026-08-24T00:00:00")
    result = compare("A4261108", "candidate-2")
    assert result["pairs"][0]["count"] == 1
    assert result["pairs"][0]["time_differences_hours"][0] == pytest.approx(
        -6.0822222222
    )
    assert result["pairs"][0]["ground_mean"] == pytest.approx(10.277256944444444)


def test_future_gate_and_missing_series():
    before = compare("A4261108", "candidate-2", lag_days=3, mode="as_of")
    assert all(p["ground_mean"] is None for p in before["pairs"])
    assert any(p["blocked_future_count"] > 0 for p in before["pairs"])
    missing = compare("A4261108", "candidate-2", variable="level")
    assert missing["unit"] is None
    assert all(p["ground_mean"] is None for p in missing["pairs"])


def test_radar_correlation_guard_does_not_count_repeated_daily_samples():
    result = correlation_summary(list(range(60)), list(range(60)), independent_epochs=3)
    assert result["status"] == "INSUFFICIENT DATA"
    assert result["pearson"] is None and result["p_value"] is None


def test_chronological_covariate_benchmark_preserves_holdout():
    data, _ = load_data()
    for station in data["stations"]:
        result = daily_covariates(station)
        assert result["n"] == 53
        assert result["evaluation"]["training_days"] == 35
        assert result["evaluation"]["test_days"] == 18
        metrics = result["evaluation"]["metrics"]
        assert (
            metrics["previous_day_persistence"]["mae_mg_l"]
            < metrics["temperature_association"]["mae_mg_l"]
        )
        assert result["p_value"] is None


def test_oxygen_mass_balance_and_closed_box_limits():
    result = simulate(
        Scenario(
            initial_demand_mg_l=0,
            incoming_demand_mg_l=0,
            exchange_per_day=0,
            reaeration_20_per_day=0,
        )
    )
    np.testing.assert_allclose(result["oxygen_mg_l"], 9)
    demanding = simulate(
        Scenario(
            initial_demand_mg_l=40,
            incoming_demand_mg_l=0,
            exchange_per_day=0,
            reaeration_20_per_day=0,
        )
    )
    assert demanding["minimum_oxygen_mg_l"] >= -1e-7
    assert demanding["mass_balance_max_error_mg_l"] < 1e-6
    initial_total = 9 - 40
    np.testing.assert_allclose(
        np.array(demanding["oxygen_mg_l"]) - np.array(demanding["demand_mg_l"]),
        initial_total,
        atol=1e-6,
    )


def test_equilibrium_reference_and_scenario_controls():
    assert float(freshwater_equilibrium(20)) == pytest.approx(9.092, abs=0.01)
    assert freshwater_equilibrium(10) > freshwater_equilibrium(25)
    low = simulate(Scenario(initial_demand_mg_l=2))
    high = simulate(Scenario(initial_demand_mg_l=25))
    assert high["minimum_oxygen_mg_l"] < low["minimum_oxygen_mg_l"]
    with pytest.raises(ValueError):
        simulate(Scenario(exchange_per_day=-1))


def test_api_contract_and_finite_json():
    for endpoint in [
        "/api/catalog",
        "/api/investigate",
        "/api/covariates/A4261108",
        "/api/report",
        "/api/default-scenario",
    ]:
        response = client.get(endpoint)
        assert response.status_code == 200
        json.dumps(response.json(), allow_nan=False)
    assert client.get("/api/investigate?station=unknown").status_code == 404
    assert client.get("/api/investigate?lag=99").status_code == 422
    assert client.post("/api/simulate", json={"temperature_c": 80}).status_code == 422
    assert client.get("/").status_code == 200
