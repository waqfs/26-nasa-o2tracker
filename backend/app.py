"""Portable local API for O2tracker."""

from dataclasses import asdict
from functools import lru_cache
from oxygen_debt.flood import FloodExperiment, experiment
from oxygen_debt.essentiality import dossier, digest
from oxygen_debt.flood_context import context as flood_context, reveal as flood_reveal
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from oxygen_debt.settings import PROJECT_ROOT, SNAPSHOT_ROOT, read_json
from oxygen_debt.investigation import compare, daily_covariates, load_data
from oxygen_debt.models import Scenario, simulate

app = FastAPI(title="O2tracker", version="0.4.0")


class ScenarioRequest(BaseModel):
    temperature_c: float = Field(20, ge=0, le=40)
    initial_oxygen_mg_l: float = Field(9, ge=0, le=20)
    initial_demand_mg_l: float = Field(8, ge=0, le=100)
    incoming_oxygen_mg_l: float = Field(9, ge=0, le=20)
    incoming_demand_mg_l: float = Field(2, ge=0, le=100)
    exchange_per_day: float = Field(0.2, ge=0, le=5)
    decay_20_per_day: float = Field(0.15, ge=0, le=5)
    reaeration_20_per_day: float = Field(0.5, ge=0, le=5)
    days: float = Field(14, gt=0, le=60)


class FloodRequest(BaseModel):
    area_ha: float = Field(100, ge=1, le=2000)
    depth_m: float = Field(0.5, ge=0.1, le=3)
    exchange_per_day: float = Field(0.1, ge=0, le=1)
    river_flow_m3_s: float = Field(100, ge=1, le=1000)
    river_volume_ml: float = Field(5000, ge=100, le=50000)
    connected_fraction: float = Field(0.5, ge=0, le=1)
    hydrology_spread: float = Field(0.5, ge=0, le=0.9)
    upstream_oxygen_mg_l: float = Field(9, ge=0, le=15)
    station: Literal["A4261108", "A4261053"] = "A4261108"
    location: str = "candidate-2"
    pass_index: int = Field(1, ge=0, le=2)
    use_boundary_measurements: bool = False
    evidence_arm: Literal["A", "B", "C"] = "C"


@lru_cache(maxsize=16)
def cached_experiment(configuration):
    return experiment(configuration)


@app.get("/api/flood-evidence")
def flood_evidence(
    station: Literal["A4261108", "A4261053"] = "A4261108",
    location: str = "candidate-2",
    pass_index: int = Query(1, ge=0, le=2),
):
    try:
        return flood_context(station, location, pass_index)
    except StopIteration:
        raise HTTPException(404, "Unknown location")


@app.post("/api/flood-experiment")
def calculate_flood(request: FloodRequest):
    inputs = request.model_dump()
    arm = inputs.pop("evidence_arm")
    station = inputs.pop("station")
    location = inputs.pop("location")
    pass_index = inputs.pop("pass_index")
    use = inputs.pop("use_boundary_measurements")
    try:
        context = flood_context(station, location, pass_index)
    except StopIteration:
        raise HTTPException(404, "Unknown location")
    if use:
        boundary = context["boundary_inputs"]
        if any(boundary[k]["observation"] is None for k in ["oxygen", "temperature"]):
            raise HTTPException(422, "No GOOD aligned upstream boundary data")
        inputs["upstream_oxygen_mg_l"] = boundary["oxygen"]["observation"]["value"]
        inputs["temperature_c"] = boundary["temperature"]["observation"]["value"]
    core = cached_experiment(FloodExperiment(**inputs))
    result = dict(core)
    result["model_output_sha256"] = digest(core)
    result["evidence_arm"] = arm
    result["nisar_constrained_parameters"] = []
    result["arm_scope"] = (
        "Only evidence visibility changes. Same time anchor, physical parameters and random draws; no NISAR-to-inundation conversion."
    )
    result["boundary_context"] = context["boundary_inputs"] if use else None
    result["boundary_caution"] = context["boundary_caution"]
    result["measured_target_oxygen_used"] = False
    return result


@app.get("/api/flood-reveal")
def reveal_flood(
    station: Literal["A4261108", "A4261053"] = "A4261108",
    location: str = "candidate-2",
    pass_index: int = Query(1, ge=0, le=2),
    mode: Literal["retrospective", "as_of"] = "retrospective",
    evidence_arm: Literal["A", "B", "C"] = "C",
):
    try:
        result = flood_reveal(station, location, pass_index, mode)
        if evidence_arm != "C":
            result["selected"].pop("radar_db", None)
            result["selected"].pop("granule_id", None)
        return result
    except StopIteration:
        raise HTTPException(404, "Unknown location")


@app.get("/api/essentiality")
def essentiality(
    location: str = "candidate-2",
    pass_index: int = Query(1, ge=0, le=2),
    arm: Literal["A", "B", "C"] = "C",
):
    try:
        return dossier(location, pass_index, arm)
    except StopIteration:
        raise HTTPException(404, "Unknown location")


@app.get("/api/ablation")
def ablation():
    return read_json("derived/nisar_ablation.json")


@app.get("/api/health")
def health():
    return dict(
        status="ok",
        release="0.4.0-rc1",
        product="O2tracker",
        scientific_scope="Educational experiment; no event-specific forecast",
    )


@app.get("/api/catalog")
def catalog():
    station_data, radar_data = load_data()
    return dict(
        stations=station_data["stations"],
        locations=radar_data["locations"],
        missing_drivers=station_data["missing_drivers"],
        granules=read_json("provenance/request.json")["acquisitions"],
        hypothesis="Do NISAR changes add explanatory or predictive information about independently measured dissolved oxygen?",
        verdict="INSUFFICIENT DATA for a radar–oxygen relationship with three independent radar dates",
    )


@app.get("/api/investigate")
def investigate(
    station: str = "A4261108",
    location: str = "candidate-2",
    variable: Literal["oxygen", "temperature", "level"] = "oxygen",
    polarization: Literal["HHHH", "HVHV"] = "HHHH",
    lag: int = Query(0, ge=-14, le=21),
    window: int = Query(1, ge=1, le=7),
    mode: Literal["retrospective", "as_of"] = "retrospective",
):
    try:
        return compare(station, location, variable, polarization, lag, window, mode)
    except StopIteration:
        raise HTTPException(404, "Unknown station or location")


@app.get("/api/covariates/{station}")
def covariates(station: str):
    data, _ = load_data()
    try:
        return daily_covariates(next(s for s in data["stations"] if s["id"] == station))
    except StopIteration:
        raise HTTPException(404, "Unknown station")


@app.post("/api/simulate")
def simulation(request: ScenarioRequest):
    return simulate(Scenario(**request.model_dump()))


@app.get("/api/default-scenario")
def default_scenario():
    return simulate(Scenario())


@app.get("/api/report")
def report():
    data, _ = load_data()
    return dict(
        title="O2tracker · Katarapko–Pike evidence report",
        verdict="INSUFFICIENT DATA for radar–oxygen inference",
        covariates={s["id"]: daily_covariates(s) for s in data["stations"]},
        science=(PROJECT_ROOT / "SCIENCE.md").read_text(encoding="utf-8"),
        flood_methods=(PROJECT_ROOT / "docs/FLOOD_EXPERIMENT.md").read_text(
            encoding="utf-8"
        ),
        essentiality=read_json("derived/nisar_ablation.json"),
    )


@app.get("/")
def home():
    return FileResponse(PROJECT_ROOT / "frontend/landing.html")


@app.get("/app")
def radar_app():
    return FileResponse(PROJECT_ROOT / "frontend/o2.html")


@app.get("/investigation")
def investigation_page():
    return FileResponse(PROJECT_ROOT / "frontend/index.html")


@app.get("/case-studies")
def case_studies_page():
    return RedirectResponse("/app#evidence")


@app.get("/api/case-studies")
def case_studies():
    return read_json("derived/case_studies.json")


@app.get("/methods/essentiality")
def essentiality_methods():
    return FileResponse(
        PROJECT_ROOT / "docs/NISAR_ESSENTIALITY.md",
        media_type="text/plain; charset=utf-8",
    )


@app.get("/methods/flood")
def flood_methods():
    return FileResponse(
        PROJECT_ROOT / "docs/FLOOD_EXPERIMENT.md",
        media_type="text/plain; charset=utf-8",
    )


@app.get("/docs/{name}")
def document(name: str):
    if name not in [
        "SCIENCE.md",
        "DATA_SOURCES.md",
        "REPRODUCIBILITY.md",
        "LIMITATIONS.md",
        "AI_DISCLOSURE.md",
    ]:
        raise HTTPException(404, "Unknown document")
    return FileResponse(PROJECT_ROOT / name, media_type="text/plain; charset=utf-8")


app.mount("/assets", StaticFiles(directory=PROJECT_ROOT / "assets"), name="assets")
app.mount(
    "/frontend", StaticFiles(directory=PROJECT_ROOT / "frontend"), name="frontend"
)
app.mount("/data", StaticFiles(directory=SNAPSHOT_ROOT), name="data")
