# CANOPY-PULSE scientific verdict

Archived scientific report from the previous implementation. Paths and reproduction commands in its historical text refer to that workspace; use the current REPRODUCIBILITY.md for this public checkout. The scientific limitations and failed/inconclusive results below remain part of the current evidence record.

**The central claim that adding NISAR improves inundation monitoring remains INCONCLUSIVE.** The project demonstrates reproducible NISAR HH/HV change measurements and independent water-level rises at two wetlands. A selected retrospective Landsat-label test produced a higher ROC AUC when NISAR was added. Its precision and uncertainty audits prevent a confirmed advantage claim.

The previous narrow September PASS is withdrawn. Feature observations after the reference date make the test retrospective, and its buffered gain interval includes zero after adjustment across nine recorded exploratory settings.

| Claim | Verdict | Basis |
|---|---|---|
| Reproducible radar-change measurements | PASS | Twelve science/QA TIFF hashes, compatible metadata, masks, looks and grids checked. Four native change maps independently recomputed. |
| Wetland water levels rose during watering | PASS | GOOD-grade field visits at Ngak-Indau and Carparks Lagoon. |
| September result demonstrates advance prediction | FAIL | September 26–29 features follow September 24 reference labels. |
| August 23 is a pre-watering baseline | FAIL | NPWS reported operations underway on August 13. |
| NISAR adds predictive or mapping value | INCONCLUSIVE | Selected ROC improvement, declining September AP, exploratory multiplicity, one event and temporal mismatch. |
| Verified subcanopy flood detection | INCONCLUSIVE | Reference stations lie outside ranked candidate blocks. Optical products cannot establish water beneath canopy. |
| Improved management information or decisions | INCONCLUSIVE | No independent decision outcome was evaluated. |
| Improved water-quality modeling | INCONCLUSIVE | No evaluated oxygen forecast. Measured oxygen does not establish a blackwater event. |

## Observation timing and leakage audit

Every image feature, context acquisition and reference image has an exact UTC observation timestamp and identifier in outputs/validation/observation_timeline.csv. Product creation is recorded where preserved. Historical public availability remains unverified. Exact timestamps come from retained CMR/STAC records rather than filenames alone.

- NISAR features use 23 August 20:34:56 UTC and 28 September 20:34:56 UTC. The 10 October acquisition supplies context and is excluded from both benchmarks.
- Sentinel-1 features use 21 August 19:56:32.949617 UTC and 26 September 19:56:34.142711 UTC. The 8 October image supplies context.
- Sentinel-2 features use two tile observations on 23 August 00:46:24.483–00:46:39.101 UTC and 29 September 00:46:41.539–00:46:56.161 UTC. The 7 October image supplies context.
- The baseline Landsat eligibility image is 23 August 00:27:09.203619 UTC. Target images are 24 September 00:27:21.076780 UTC and 2 October 00:27:28.857154 UTC.
- The 14 July Sentinel-2 images inform earlier optical context and are excluded from benchmark predictors. Field visits occurred at their actual source timestamps in station_joins.json. Daily station aggregates retain fixed UTC+09:30 and are contextual rather than exact overpass observations.

For September, all three sensor endpoints occur after the target. NISAR follows it by about 4 days 20 hours, and Sentinel-2 by about 5 days. This is retrospective cross-date association. Any use as advance prediction would introduce temporal leakage. October feature acquisitions precede the target, but model training/evaluation uses the same event and historically available delivery times are unverified. Therefore it also supports only retrospective evaluation. The model sees labels from training locations in that event. There is no held-out future event.

Landsat labels supply no predictor column. August dry flags and both dates' clear flags condition the eligible population, and target water/dry fractions define positive and negative classes. This omits ambiguous/cloud-covered blocks and creates a selected population. Sentinel-2 and Landsat classification errors can be correlated. The Sentinel-2 proxy experiment excludes its target from predictors but still evaluates optical agreement. None of these labels supplies independent canopy inundation truth.

## Spatial design, class balance and statistics

The common grid has 100 m blocks derived from 20 m linear power. Five interleaved folds hold out complete 5 km geographic tiles. Unbuffered train/test tiles touch, so all six Landsat settings were rerun excluding training samples within more than 1 km of held-out tiles. Both models use identical partitions and eligibility. Training-fold means/standard deviations and balanced class weights are fitted using training rows only. The fixed regularized logistic model is used across settings. Evaluation retains the observed class imbalance. Scores are rankings, with no probability calibration or operating threshold.

Conventional predictors are Sentinel-1 VV/VH changes plus two Sentinel-2 water fractions. The extended model adds NISAR HH/HV changes. A 40%, 60% or 80% minimum Landsat wet fraction defines positives. Target clear dry fraction ≥90% defines negatives. Baseline dry fraction ≥80%, target clear fraction ≥90% and both Sentinel-2 clear fractions ≥90% are required. Each output records eligible counts, positive tiles, fold assignments and training/test counts. This setting isolates added features in a fixed algorithm, not the best possible conventional model. Geometry, polarization and timing confound wavelength attribution.

ROC AUC and threshold-grouped average precision (AP) are reported together. The prior row-order treatment of tied scores was corrected. It changed these displayed AP values by less than 0.001. AP's no-skill reference is the eligible positive prevalence, approximately 0.14–1.51% across these six settings. Average precision can expose limitations hidden by ROC AUC in this imbalanced sample.

| Target | Wet fraction | Positive / negative blocks | ROC AUC conventional / +NISAR | AP conventional / +NISAR | Buffered ROC AUC conventional / +NISAR | Buffered AUC-gain interval, nine-setting adjustment |
|---|---:|---:|---:|---:|---:|---:|
| 2026-09-24 | 40% | 401 / 65280 | 0.661 / 0.671 | 0.190 / 0.188 | 0.628 / 0.630 | -0.058 to +0.081 |
| 2026-09-24 | 60% | 207 / 65280 | 0.688 / 0.720 | 0.323 / 0.321 | 0.661 / 0.684 | -0.053 to +0.103 |
| 2026-09-24 | 80% | 92 / 65280 | 0.770 / 0.824 | 0.549 / 0.545 | 0.746 / 0.784 | -0.003 to +0.087 |
| 2026-10-02 | 40% | 1731 / 53462 | 0.568 / 0.612 | 0.053 / 0.059 | 0.558 / 0.605 | -0.018 to +0.116 |
| 2026-10-02 | 60% | 1221 / 53462 | 0.581 / 0.624 | 0.033 / 0.039 | 0.570 / 0.616 | -0.023 to +0.118 |
| 2026-10-02 | 80% | 811 / 53462 | 0.597 / 0.621 | 0.023 / 0.026 | 0.586 / 0.611 | -0.045 to +0.105 |


For the selected strict September setting, the unbuffered AUC rises 0.770 to 0.824 while AP falls 0.549 to 0.545. With buffering, AUC rises 0.746 to 0.784 and AP falls 0.515 to 0.513. The buffered AUC-gain 95% conditional interval is +0.006 to +0.068. Its nine-setting adjusted interval is −0.003 to +0.087. The latter includes zero.

The six Landsat settings and three previously inspected Sentinel-2 settings were exploratory. We use Bonferroni sensitivity intervals at 1−0.05/9 (99.444% each) to acknowledge this recorded family. Later model/buffer choices add exploration, so these intervals do not turn the study into confirmatory inference. Bootstrap resamples geographic tiles in pairs 2,000 times with fixed out-of-fold scores and a fixed seed. It omits model-refitting, temporal-event and source-label uncertainty. Low positive-tile counts (nine in the selected setting) further limit inference. Neither evaluation date supplies an independent temporal replication because both belong to the same event and use the same predictor endpoints. Dropping each positive tile from the selected fixed-score evaluation leaves ROC gains of +0.043 to +0.059, which does not resolve the precision or multiplicity limitations.

Saved scores_*.npz files include row, column, tile, fold, labels and predictions for all six settings. The supplementary Sentinel-2 experiment had gains at only one of three thresholds. The full family, confidence intervals, model code and chronology remain inspectable.

## Independent field observations

GOOD-grade visits on 2 and 24 September measured Ngak-Indau levels rising from 1.973 to 2.230 m (+0.257 m) and Carparks Lagoon from 0.465 to 1.018 m (+0.553 m). Levels use each station's own datum. The September 24 visits precede NISAR by about 4.8 days. The nearest candidate centre is 399 m from Ngak-Indau. None of the six examined stations lies inside a ranked 100 m block. Their coordinates, grades and observation times are retained.

The surrounding nine-block median HH changes were −1.216 dB at Ngak-Indau and −0.417 dB at Carparks. Rising wetland levels therefore coexist with falling backscatter in these mixed-cover neighborhoods. This constrains simple interpretations without assigning a flood label to candidate blocks. The Ngak-Indau continuous daily values carry UNDEF grades, while the field visits independently carry GOOD grades. Only the latter establish the reported field changes.

Independent GOOD daily oxygen means were 8.92–10.74 mg/L at Katarapko and 8.42–11.15 mg/L at Pike during the retained interval. Daily means cannot establish short-duration minima, and the observations provide no demonstrated blackwater event or fish-death prevention outcome.

## Acquisition and calibration audit

All three products share full-frame joint-observation mode, ascending track 153/frame 160, frequency-A 20 MHz HH/HV, MOE orbit type, JPL PR pipeline, P05023 and GCOV 1.0.11. CMR granules are G4289277210-ASF, G4329677554-ASF and G4360923482-ASF. Complete granule filenames and source file hashes are in data/acquisition/download_manifest.json.

Native 20 m arrays are 2223×2305 in EPSG:32754. Each epoch/polarization has 5,098,518 valid pixels. Median looks are 9.87320, 9.87272 and 9.87309. For each date pair and polarization, all 25 sampled high-pass image windows align best at zero whole-pixel displacement in a ±3 pixel search. This constrains gross relative shifts at sampled locations. Absolute positioning, subpixel registration and instrumental radiometry remain unverified.

Regional August–September HH median change is −1.482 dB on the matched grid. Historical built-up reference proxies also change −0.801 dB (601 blocks), and bare/sparse proxies −1.083 dB (482 blocks). Assuming either as a uniform offset leaves −0.681 or −0.399 dB. These are sensitivity calculations, with no correction applied. Moisture and structure can change reference proxies. Instrument/processing effects could explain part of the shared shift, but their magnitude is unidentifiable here.

ASF reports residual RFI/ripples and incomplete-L0B issues in provisional products. Relative-phase correction leaves diagonal powers unaffected, and the 40 MHz warning refers to a different bandwidth. The incomplete-L0B issue was corrected in P05036. No replacement validated granules intersected the requested stack/date interval in the retained query. Subsets lack complete raw telemetry and invariant reference targets. The August baseline was already within the managed-watering season.

## Reproduction and outputs

Run from the repository root with .venv. With retained inputs, execute python -m scripts.validation_comparison followed by python -m scripts.submission_audit. The metrics script writes fold scores and all six results. The audit writes observation_timeline.csv, submission_audit.json and the application's validation.json. For raw processing use README.md. Independent-input acquisition is described in [docs/REPRODUCIBILITY.md](REPRODUCIBILITY.md).

All analytical rasters, model rankings and field plots carry observed/derived/modeled labels in the final demonstration. The 3D terrain is the Copernicus GLO-30 digital surface model sampled every 400 m, with visually exaggerated relief. It includes canopy and structures. Radar-change color is derived from measured power. Only logistic ranking scores are modeled.

## Primary sources

- [NASA/ASF GCOV](https://nisar-docs.asf.alaska.edu/gcov/) and [Harmony](https://nisar-docs.asf.alaska.edu/harmony/)
- [Provisional limitations](https://nisar-docs.asf.alaska.edu/provisional-known-issues/) and [P05036 corrections](https://nisar-docs.asf.alaska.edu/nisar-known-issues/)
- [DEW observations](https://water.data.sa.gov.au/) and [station coordinate metadata](https://location.sa.gov.au/LMS/Reports/ReportMetadata.aspx?p_no=1931&pu=y)
- [NPWS 13 August closure](https://www.parks.sa.gov.au/know-before-you-go/closures-and-alerts/murray-river-national-park-katarapko-3) and [9 October DEW operations report](https://www.waterconnect.sa.gov.au/Content/Flow%20Reports/RM-Flow-Report_2026_10_09%20FINAL.pdf)
- [DEA water interpretation](https://knowledge.dea.ga.gov.au/notebooks/DEA_products/DEA_Water_Observations/)
- [Copernicus DEM](https://registry.opendata.aws/copernicus-dem/)
