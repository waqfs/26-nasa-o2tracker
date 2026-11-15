# O2tracker

**See what changes beneath the surface — with real NASA NISAR radar.**

O2tracker makes NASA NISAR L-band radar observations explorable. Open it and you are looking at real data: three NISAR backscatter acquisitions over the Katarapko–Pike floodplain (South Australia) with a checked before/after comparison and difference view, and eight 12-day interferometric pairs over the Everglades (WCA-3A, Florida) showing coherence and unwrapped phase with water-level gauges. Click any pixel to read its decoded value and coordinates.

- **Explore** — real NISAR GCOV and GUNW rasters on their native UTM grids, acquisition timeline (including archive gaps), HH/HV, before/after slider, difference, coherence, phase, provenance.
- **Evidence** — an exploratory withheld-gauge test (E15): NISAR-assisted water-level-change RMSE 2.31 cm vs 3.43 cm for the strongest gauge-only baseline we tested, with placebo, failed replication and limits shown alongside.
- **Why it matters** — measured low dissolved oxygen in Louisiana (CPRA field profiles; a different site). No NISAR-to-oxygen relationship is established.
- **About** — methods, sources, labels (Observed / Derived / Modeled / Exploratory) and the original Katarapko investigation at /investigation.

O2tracker is not an oxygen sensor, hypoxia predictor or early-warning service. This project was developed as OXYGEN DEBT so historical records may contain that name. Viewer assets are built deterministically by scripts/build_viewer_assets.py from the original NISAR rasters (not redistributed); data/derived/viewer/manifest.json records geotransforms, encodings and source SHA-256 values.

---

O2tracker is an interactive scientific investigation. It connects real NISAR HH/HV observations over Katarapko/Pike, South Australia, with independently measured dissolved oxygen, temperature and water level during the 2026 environmental-watering season.

The new experiment moves from independent flood evidence to a finite-carbon oxygen budget, conditional uncertainty, an explicit oxygen reveal and output-specific sensitivity. Published litter/chemistry bounds are separated from assumed hydrology. NISAR does not supply a validated flooded-area input here. Read docs/FLOOD_EXPERIMENT.md for the complete model and results.

Follow the Oxygen moves from the radar landscape to the river sensor. Select an area, station, polarization, acquisition, variable and lag. Reveal measured oxygen, inspect time offsets and geographic separation, explore competing explanations, then experiment with an explicitly educational oxygen-budget model. There are three independent radar dates. Two stations supply 53 GOOD-grade oxygen daily means each, ranging 8.918–10.737 and 8.422–11.149 mg/L.

## What changes if NISAR is removed?

**The present oxygen model does not change.** Three controlled evidence arms produce identical complete numerical outputs under fixed assumptions, including a matched upstream-data check. NISAR is supportive of a surface-change investigation; its quantitative oxygen benefit remains unproven.

Switch A/B/C in the app, remove NISAR from a live calculation and inspect its unchanged fingerprint. Compare actual HH/HV changes against conventional observations and reference proxies, then choose which missing observation would distinguish water, soil/vegetation, radiometric effects or the outlet-to-river oxygen pathway. The dependency map marks the unsupported radar-to-inundation link explicitly. This is a scientific limitation exposed through an interactive investigation, not a validated warning system. Read docs/NISAR_ESSENTIALITY.md.

## Run locally

Python 3.13 was used. From this directory, create and activate a virtual environment, then run:

```sh
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8010
```

Open http://127.0.0.1:8010 for the landing page; the radar viewer and its sections are at http://127.0.0.1:8010/app. The original Katarapko investigation is at http://127.0.0.1:8010/investigation. The supplied small source/derived snapshots support the complete application without Earthdata credentials. Node is only needed for optional JavaScript syntax checks. No JavaScript build or external LLM is required.

```sh
python scripts/run_investigations.py
python scripts/run_flood_experiment.py
python scripts/run_ablation.py
python scripts/audit_model.py
python -m pytest -q
npm run check
```

See REPRODUCIBILITY.md for source verification, optional raw radar processing and the external-data configuration. Fresh radar acquisition requires Earthdata authentication in the local terminal. No credentials are bundled.

## What is implemented

- Six observed HH/HV terrain layers from three actual NISAR acquisitions, with provenance and quality information.
- Two verified oxygen stations, recorded quality grades, exact time zones, missing-data handling and source files.
- Area-to-station distance, retrospective windows and a recorded-timestamp as-of gate. Hydraulic connectivity remains unverified.
- A deliberate radar-correlation guard, descriptive daily covariates, and a chronological temperature benchmark against simple baselines.
- A 512-member educational floodplain/river experiment with finite litter carbon, published parameter bounds, conservative transport, adaptive numerical checks and conditional Jansen sensitivity. The previous single-box lesson remains accessible.
- Exportable evidence reports, eight linked story scenes, desktop/mobile controls and a local demonstration.

Historical radar methods and negative outcomes remain available in docs/PRIOR_RADAR_RESULTS.md with the retained evaluation code and manifests.

## License

Project code uses the MIT license. External datasets retain their original rights and attribution.

Read DATA_SOURCES.md.

## AI Disclosure

Read AI_DISCLOSURE.md.
