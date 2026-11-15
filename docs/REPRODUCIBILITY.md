# Reproduce O2 Tracker

## Supplied-data analysis

Install requirements.txt and the local package as described in README.md. From this repository root:

```sh
python scripts/prepare_observations.py
python scripts/run_investigations.py
python -m pytest -q
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8010
```

The first command uses retained original source responses and cached official coordinates. It only requests a coordinate summary when that cached metadata is absent. Source grades, units and missing records are preserved. The second command regenerates all 0/3/7-day comparisons, descriptive daily correlations, chronological benchmarks and the default educational scenario. No radar–oxygen correlation is fitted. Numerical results are deterministic from this snapshot.

## External raw data

Set OXYGEN_DATA_ROOT to the directory containing raw/ outside this repository. Do not point it at a personal path committed into configuration. In PowerShell, use the environment variable for the current process. In a POSIX shell use export.

```sh
python scripts/prepare_radar_layers.py
```

This rebuilds the six radar visualization layers from actual science and QA files using the published job manifest. Shapes, mask semantics and positive power/looks are checked by the reused readers. Native files are excluded from this repository. To download again, use:

```sh
python -m canopy_pulse.acquire --prepare-only
python -m canopy_pulse.acquire --login
```

Enter Earthdata credentials only in your terminal. The acquisition module retains source metadata and downloads science subsets. Without OXYGEN_WORKSPACE_ROOT it uses this repository; selection falls back to data/provenance. When reconstructing the complete legacy radar workspace, OXYGEN_WORKSPACE_ROOT can point to a separate directory with the documented data/acquisition, data/raw and outputs layout. No fixed developer path is required.

For native before/after processing, generate a local configuration from the exact Harmony manifest:

```sh
python scripts/prepare_pair.py --before 2026-08-23 --after 2026-09-28 --polarization HHHH
python -m canopy_pulse.process outputs/local/pair.json --output outputs/local/native-aug-sep
```

The inventory falls back to the supplied provenance snapshot. The generated local pair file uses the configured raw power/mask/looks files and is excluded from Git. Outputs require a new or empty directory. Inputs must be calibrated power with confirmed subswath masks. Source COG paths in the published manifest are portable slash-separated paths relative to the chosen workspace. Optional source HDF5 configurations are also supported.

The prior surface-water ranking experiment and its unsuccessful predefined forward evaluation are preserved in docs/PRIOR_RADAR_RESULTS.md, data/derived and published validation scripts. Raw comparison TIFFs must be downloaded before rerunning that experiment. It is separate from the Oxygen Debt inference, which remains sample-limited.

## Software and presentation

Tests distinguish implementation behavior from environmental validation. Browser checks exercise both stations, variable/lag controls, blocked future observations, exported reports, educational model changes, terrain switching and narrow layout. The demo uses Matplotlib's bundled DejaVu Sans font. scripts/audit_public.py records SHA-256 hashes for the public files; tests separately verify the source-response hashes against the observation manifest.

```sh
python scripts/check_application.py
python scripts/audit_public.py
```

Browser checks use an installed Microsoft Edge browser through Playwright, and the server must already be running.

## Finite-carbon flood experiment

The supplied data run needs no authentication or raw radar files:

```sh
python scripts/acquire_flood_context.py
python scripts/run_flood_experiment.py
python -m pytest -q
python scripts/check_application.py
python scripts/check_flood_experiment.py
```

acquire_flood_context.py without --live verifies the four retained response hashes and regenerates boundary context. --live explicitly refreshes the selected official datasets and responses; changing sources may change numerical results/grades. No credential is required for these DEW requests.

run_flood_experiment.py regenerates default, disconnected and low-flow/large-area stress scenarios with fixed PCG64 seed 20261115 and 512 members each. No target oxygen is used in these calculations. It writes data/derived/flood_experiment.json. The numerical step adapts using the first 32 members' minimum-river refinement check; each output records the step and diagnostic. Jansen total-order indices and 200 paired bootstrap resamples accompany two distinct outputs. All parameter bounds and model assumptions remain in the JSON and docs/FLOOD_EXPERIMENT.md.

To repeat the native radar audit without overwriting prior outputs, set OXYGEN_WORKSPACE_ROOT to an external legacy-layout workspace containing data/acquisition, data/raw and outputs/comparison, then run from this checkout:

```sh
python -c "import os; from canopy_pulse.audit import main; main(os.environ['OXYGEN_WORKSPACE_ROOT'], 'outputs/local/rechecked-radar')"
python scripts/prepare_flood_evidence.py --workspace <external-workspace> --radar-audit outputs/local/rechecked-radar/radar_audit.json
```

The native audit verifies hashes, masks/looks, geometry and proxy reference changes. The second command checks independent Landsat raster hashes/grid and extracts each candidate's support. It never converts radar to inundated area.

## Essentiality release

```sh
python scripts/run_ablation.py
python scripts/audit_model.py
python scripts/check_essentiality.py --url http://127.0.0.1:8010
```

run_ablation.py independently reruns the default solver for A/B/C, followed by a labeled secondary matched-GOOD-upstream dependency control. It fixes locations, anchors, parameters, seed and equations across arms. There is no fitting or new classification search. Model fingerprints normalize equivalent int/float representations without rounding unequal floating values. The current artifact should reproduce exactly from the supplied snapshots.

audit_model.py runs all 512 base members in each retained default/disconnected/stress scenario at the saved and half steps, checks the declared minimum-river difference and carbon/oxygen/water-boundary ledgers. This does not cover all sensitivity hybrids or validate field assumptions.
