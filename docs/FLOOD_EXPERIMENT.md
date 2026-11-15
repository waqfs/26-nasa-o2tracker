# Could This Flood Have Done It?

This is an educational counterfactual using the actual 2026 Katarapko/Pike evidence as context. **It is not an event-specific flooding estimate or oxygen prediction.** The model does not use target-station oxygen until a separate reveal request. A visible hidden outcome is an interaction device, not a blinded independent scientific trial: the historical outcomes were already known to the developers.

## Evidence before calculation

Current official CMR identities, acquisition times and geometry were programmatically rechecked for all three concept IDs, with matches retained in data/provenance/nisar_metadata_recheck.json. The three native radar acquisitions were re-audited from the retained 12 science/QA files. The regenerated audit is numerically identical to the prior audit. All share ascending track 153/frame 160, frequency-A HH/HV 20 MHz, full-frame joint mode, JPL PR pipeline, P05023, GCOV 1.0.11 and MOE orbit metadata. Native arrays are 2223 by 2305 at 20 m, EPSG:32754; each retained polarization/epoch has 5,098,518 valid pixels. Median looks are 9.87320, 9.87272 and 9.87309. The 25 sampled windows per date-pair/polarization prefer zero integer-pixel displacement; absolute and subpixel alignment are unverified.

On common 100 m support, August-September regional HH median change is -1.481926 dB. Built-up proxies decline -0.800902 dB (601 blocks), bare/sparse proxies -1.083293 dB (482), and tree proxies -1.015504 dB (17,876). These proxies were selected by WorldCover/Sentinel-2 land support without radar-change filtering. They are not invariant calibration targets. Assuming built/bare offsets would leave -0.681024/-0.398633 dB regionally; no correction is applied. Environmental moisture, common radiometric components and provisional artifacts cannot be separated here.

NASA/ASF provisional guidance was rechecked: residual RFI, ripples and incomplete L0B are relevant unresolved possibilities. The polarimetric phase adjustment leaves HHHH/HVHV powers unaffected. The 40 MHz joint-mode warning concerns another bandwidth; the listed diagnostic frames differ from this stack. Incomplete-L0B processing is corrected in P05036 validated products, but that does not retroactively correct these P05023 inputs. No new replacement-product search was performed in this upgrade; the retained previous search found no intersecting replacement stack. No per-acquisition telemetry, independent invariant targets or validated flood conversion is available.

**Decision: radar power is usable for exploratory measured change; quantitative flooded area/depth from these observations is UNSUPPORTED.** It is not supplied to the mass budget as a measured flooding input.

Six original field-visit responses and exact request/hash mappings are retained in data/observations and data/provenance/field_visit_manifest.json. The preparation checks every displayed visit against those source rows. Independent GOOD field visits establish level rises at Ngak-Indau (+0.257 m) and Carparks (+0.553 m) between September 2 and 24. These levels use station datums and do not provide candidate-block water depth, volume or a map of flooded area. Nearby visits shown in the app are filtered to timestamps at/before the selected radar pass. None of the original six stations lies within a ranked candidate block. August was already in the watering season.

DEA Landsat Water Observations for August 23, September 24 and October 2 provide derived clear exposed-water labels. The new preparation script verifies the retained raster hashes, CRS/grid and exact candidate support, then records 25 resampled 20 m cells per 100 m block. Original Landsat support is nominally 30 m; these are not independent 20 m field labels. Clear dry=0 and clear water=128 only. Missing/clouded support is unknown, never dry. Water fraction among clear cells and the full-block clear fraction are displayed separately. Dates do not coincide with the September/October NISAR passes; complete source timestamps remain in the manifest. They cannot establish subcanopy inundation. The failed frozen forward label experiment remains published with zero eligible classes.

## Published quantities and scenario assumptions

[Gibbs, Wallace & Mosley (2022), Table 1, p.4](https://doi.org/10.1002/hyp.14529) reports uniform sensitivity bounds. These are regional literature/model-study bounds, not posterior distributions for 2026. The numeric table and source PDF hash are in data/provenance/flood_parameters.json:

| Quantity | Bounds | Unit |
|---|---:|---|
| Readily leaching litter | 0-1000 | g dry litter/m2 |
| Slower leaching litter | 0-3000 | g dry litter/m2 |
| Fast/slow maximum DOC yield | 45-125 / 4.5-12.5 | mg C/g dry litter at 20 C |
| Fast/slow release coefficient | 0.5-0.99 / 0.05-0.3 | 1/day at 20 C |
| DOC decomposition coefficient | 0.02-0.3 | 1/day at 20 C |
| Reaeration coefficient | 0.01-0.08 | 1/day at 20 C |
| Water temperature | 10-25 | Celsius |

The fast/slow litter categories control leaching, not independently measured biochemical fractions. All released DOC is treated as biodegradable on the sampled decay timescale. This strong structural assumption omits refractory DOC, and can overstate short-term microbial demand.

[DODOC source](https://github.com/flowmatters/dodoc-source), pinned to the commit in the provenance manifest, supplies the documented temperature relationships: release coefficient times 1.03^(T-20); yield times [0.93255+0.06745 exp(0.2047(T-20))]; decomposition times [-0.2088+0.0604T]; reaeration times 1.024^(T-20). The rounded decomposition relationship gives 0.9992 at 20 C. We retain it explicitly over 10-25 C. Carbon oxidation uses exact 32/12 kg O2/kg C, corresponding to CH2O oxidation; DODOC uses rounded 2.667. No code is vendored from that repository, which declares no license.

Flood area, depth, storage, outlet exchange, receiving-river discharge, connected fraction and initial/upstream oxygen are **user assumptions**, not inferred NASA products or values taken from Table 1. Default centers: 100 ha, 0.5 m, 0.1/day exchange, 100 m3/s river flow, 5000 ML river storage, 0.5 connected fraction, initial/upstream 9 mg/L. The hydrology range defaults to +/-50% independently for area, depth, exchange, discharge and volume; connection is center +/-0.25 clipped to [0,1]. These are illustrative scenario bounds, not empirical hydrological distributions. The interface exposes them and provides no automatic radar-to-hectares conversion. Area is not multiplied independently by a derived volume: floodplain storage is recomputed consistently as area times depth.

Queries at seven selected DEW stations found no overlapping discharge series among returned datasets; this is not an exhaustive regional search. The October 9 DEW report gives approximate current regional border flow 16.5 GL/day (=190.9722 m3/s) and Lock 1 flow 18.5 GL/day. Those are context, not local outlet or receiving-reach flows, and are excluded from model forcing. Forecasts and planned regulator heights are not observed local inputs.

Four new original daily source responses are retained for upstream River Murray sensors A4261023 and A4261024. A4261024 oxygen and temperature have 53 UNVERIFIED TELEM values and are excluded from forcing. A4261023 oxygen has 46 GOOD, six UNUSABLE and two UNDEF rows; temperature has 53 GOOD and one UNDEF. Its September 29 oxygen is unusable. The optional measured-boundary mode is enabled only when both aligned oxygen and temperature are GOOD within 12 hours of the radar timestamp. These are upstream-of-outlet sensors, not proven inflows to a candidate or target station. Constant 14-day forcing, equal initial oxygen, and routing remain scenario assumptions. Target-station oxygen never supplies an upstream boundary or calibration target.

## Equations, units and conservation

Two completely mixed, fixed-volume boxes represent a floodplain and receiving river. Model time is days; all integrated carbon and oxygen masses are kg. Concentrations in mg/L equal 1000 times mass(kg)/volume(m3).

```text
Vf = area_ha * 10000 * depth_m                     [m3]
Vr = river_volume_ML * 1000                        [m3]
Qf = exchange_per_day * Vf                        [m3/day]
Qr = river_flow_m3_s * 86400                      [m3/day]
initial leachable pool Mi = area_m2 * litter_i_g_m2 * yield_i_mg_g * 1e-6 [kg C]
dMi/dt = -ki(T) Mi
release = sum(ki Mi)                               [kg C/day]
Rf = kd(T) Cf ; Rr = kd(T) Cr                     [kg C/day, oxygen limited]
```

Cf/Cr are dissolved-carbon masses. Oxygen consumption is capped by the available oxygen mass in each reaction substep; unused carbon remains. No anaerobic carbon removal is assumed. The connected fraction f of floodplain outflow reaches the river. Remaining outflow leaves the modeled system. Independent upstream supply maintains each fixed storage; the receiving-river outflow is Qr+fQf. Upstream DOC is assumed zero, so this represents added litter demand rather than all ambient river respiration.

```text
dCf/dt = release - Rf - Qf Cf/Vf
dCr/dt = f Qf Cf/Vf - (Qr+f Qf) Cr/Vr - Rr
dOf/dt = Qf (oup-Of/Vf) + ka (Osat Vf/1000 - Of) - (32/12) Rf
dOr/dt = Qr oup + f Qf Of/Vf - (Qr+f Qf) Or/Vr
          + ka (Osat Vr/1000 - Or) - (32/12) Rr
```

oup is upstream oxygen kg/m3; Osat is freshwater/standard-pressure reference mg/L using the existing APHA/QUAL2E formula. Initial Of/Or equal upstream concentration times volume. Temperature and flow are constant within each member. Day zero is displayed at the selected radar timestamp; no observed flood onset is inferred.

Finite exponential leaching, capped first-order oxidation and exponential reaeration use positive operator splitting. Conservative advection of both boxes is solved analytically, including equal-rate and zero-exchange limits. Independently integrated boundary fluxes and cumulative consumption/air exchange close the carbon/oxygen ledgers. Potential stoichiometric demand is the initial leachable carbon times 32/12; it is neither actual oxygen consumed nor river depletion.

A limited numerical diagnostic compares minimum-river oxygen at a 0.025-day step and half-step in the first 32 ensemble members. If their maximum difference exceeds 0.005 mg/L, the step is halved, up to four times. The chosen step, actual difference and warning/pass status are exported. This checks one output in a subset, not all trajectories or all possible input combinations. Low near-zero floodplain values should not be read as precise field concentrations.

## Uncertainty and sensitivity

A fixed PCG64 seed 20261115 generates 512 independent-input uniform samples (two sets of 256). The model reports 5th/median/95th percentiles, not confidence limits or calibrated probabilities. Input independence is an explicit scenario design; real area, depth, storage, flow, litter and chemistry may be correlated. Hydrological structural errors, routing uncertainty, source-label errors and missing processes are not made probabilistic by these bounds.

For each input, a pick-freeze hybrid evaluates a Jansen total-order sensitivity index for total potential stoichiometric demand and minimum receiving-river oxygen. The estimator is mean[(Y(A)-Y(A with column i from B))^2]/[2 variance(Y(A),Y(B))]. Two hundred paired row bootstrap resamples give a 95% interval for Monte Carlo estimator variability only. Total-order indices include interactions, need not sum to one, and may exceed one in finite samples. The table is an output/range-specific measurement priority, not a value-of-information calculation, a causal ranking or proof that a measurement will improve decisions. Structural omissions are not ranked.

The paired no-litter counterfactual retains the same hydrology, temperature, aeration and initial oxygen and removes the two litter pools. Its day-14 river difference isolates modeled litter effects within this simplified system. A disconnected case has no downstream carbon transport, though temperature/reaeration can still affect river oxygen. No p-values or event calibration are used.

## Reproducible findings

The frozen default yields conditional potential demand 24.217 / 127.881 / 306.569 tonnes O2 and minimum-river oxygen 8.810 / 8.965 / 9.000 mg/L (5th/median/95th). Simulated floodplain minima are 0.006 / 0.012 / 0.148 mg/L, reflecting the oxygen-limited idealization and strong biodegradable-carbon assumption. **Demand is not depletion at the river sensor:** finite loading, connectivity, replenishment, residence time and dilution all matter.

Within the declared default ranges, readily leaching litter dominates variance in total potential demand; receiving-river discharge ranks first for minimum river oxygen. Bootstrap intervals overlap other drivers; do not interpret the ordering as a precisely established field priority. Changing the ranges/output changes the ranking. The low-flow/large-area stress case (1000 ha center, 5 m3/s river flow, 500 ML river storage, connected fraction 1, spread 0.25) produces much lower simulated river oxygen. This is an explicit assumed stress scenario, not evidence those conditions occurred in 2026. Its initial time-step diagnostic failed; step refinement was required and its final diagnostic is retained.

The independent target reveal still reports Katarapko's aligned September daily mean around 9.281 mg/L, timestamp September 29 00:00 UTC+09:30, 6.082 hours before the radar timestamp. The following display window includes later GOOD daily means, shown only on request. The instantaneous model, daily averages, different spatial supports and unverified pathways do not justify an error score or model validation. Envelope overlap or disagreement cannot identify a flooding cause.

## Relationship to DODOC/BRAT and verdicts

DODOC extends BRAT concepts with hydrological node-link routing, changing wetted areas, antecedent litter accumulation and additional processes. Gibbs et al. performed regional sensitivity analysis and site monitoring. Oxygen Debt supplies a simpler two-box mechanism experiment and an evidence-to-assumption-to-reveal interface. It does not reproduce their calibrated model, their validation results or their parameter-identification study. It omits refractory DOC representation, photosynthesis, sediment demand, structure reaeration, variable inundation timing, dynamic routing and stratification. The previous single-box lesson is preserved as a secondary teaching control.

| Claim | Verdict |
|---|---|
| Native radar-change measurements reproduce | PASS |
| Field wetland levels rose at monitored locations | PASS |
| NISAR supplies a quantitative 2026 flooded area/depth | UNSUPPORTED |
| Equations conserve finite carbon and oxygen under stated boundaries | PASS, software/limiting-case checks |
| Model demonstrates conditional demand versus dilution mechanisms | PASS, educational scope |
| 2026 flood caused dangerous oxygen depletion at target stations | INCONCLUSIVE / not established |
| NISAR improves oxygen prediction or fish-death warning | UNVERIFIED |
| Broad Monte Carlo envelope validates this model | FAIL as an inference |

Source records and hashes: data/provenance/flood_parameters.json, flood_context_manifest.json, regional_flow_context.json, dea_manifest.json and jobs.json. Code: flood.py, flood_context.py, audit.py and preparation scripts. Derived evidence and default/control/stress outputs: data/derived/flood_*.json. Scientific failures and numerical diagnostics are disclosed here; private scratch outputs remain outside this repository.

Primary references: [Gibbs et al.](https://doi.org/10.1002/hyp.14529), [DODOC implementation](https://github.com/flowmatters/dodoc-source), [Mosley et al. 2021 DODOC paper](https://doi.org/10.1016/j.jenvman.2021.112213), [DEA label definitions](https://knowledge.dea.ga.gov.au/data-products/dea/613/dea-water-observations-landsat/), [DEW observations](https://water.data.sa.gov.au/), [DEW October 9 regional report](https://www.waterconnect.sa.gov.au/Content/Flow%20Reports/RM-Flow-Report_2026_10_09%20FINAL.pdf), [NASA provisional issues](https://nisar-docs.asf.alaska.edu/provisional-known-issues/), [NASA validated issues](https://nisar-docs.asf.alaska.edu/nisar-known-issues/).


## Dependency clarification

The equations and default scenario outputs above are unchanged. The sensor-removal experiment confirms that the current model receives no NISAR-constrained physical distribution. Identical A/B/C outputs and additional all-member numerical checks are documented in docs/NISAR_ESSENTIALITY.md. The new live removal control changes evidence visibility, not assumed hydrology or calibration. This clarifies the model's scope without converting NISAR context into a quantitative flood input.


Water-boundary interpretation: Qr is background channel flow entering the receiving box in addition to the independent floodplain supply Qf. If applying an upstream gauge that already includes a wetland diversion, the diversion would have to be accounted for before assigning Qr; the model does not route that operation or infer it from NISAR. Current flow values remain assumed. Continuity of the stated boundary network does not establish that this network describes the real site.
