# Data sources and rights

## NASA NISAR

Collection C2854338529-ASF, NISAR_L2_GCOV_PROVISIONAL_V1. Frequency-A HHHH/HVHV/mask/numberOfLooks, ascending track 153/frame 160, P05023, GCOV 1.0.11. Twelve native 20 m subsets totaling 233,294,873 bytes were retained externally. Exact requests, masks, layer hashes, job IDs and file identities are in data/provenance.

- G4289277210-ASF — NISAR_L2_PR_GCOV_028_153_A_160_2005_DHDH_A_20260823T203456_20260823T203531_P05023_N_F_J_001
- G4329677554-ASF — NISAR_L2_PR_GCOV_031_153_A_160_2005_DHDH_A_20260928T203456_20260928T203531_P05023_N_F_J_001
- G4360923482-ASF — NISAR_L2_PR_GCOV_032_153_A_160_2005_DHDH_A_20261010T203456_20261010T203531_P05023_N_F_J_001

Access through NASA Earthdata and Harmony. Attribution NASA/JPL and ASF DAAC. Source datasets retain their NASA use conditions. See https://nisar-docs.asf.alaska.edu/harmony/ .

## Independent river observations

South Australian Department for Environment and Water, Water Data SA. Oxygen concentration and DO-sensor water temperature at A4261108 and A4261053, plus Pike water level. Exact dataset identifiers, original request URLs, source timestamps, quality grades and snapshot hashes accompany data/derived/stations.json and data/observations. Record time zone UTC+09:30. Station-coordinate metadata URLs and GDA94 datum are preserved. DEW's location metadata describes variable positional accuracy.

Source https://water.data.sa.gov.au/ . Metadata and attribution https://location.sa.gov.au/LMS/Reports/ReportMetadata.aspx?p_no=1931&pu=y . Surface-water site metadata specifies attribution licensing. Retain DEW attribution and check current portal terms for further redistribution. The normalized snapshot retains the original observation facts and missing rows. No private account data is used.

## Other Earth observations

- Copernicus Sentinel-1 RTC, S1D orbit 162 descending, August 21 / September 26 / October 8, VV/VH. Microsoft Planetary Computer delivery, Copernicus data. https://planetarycomputer.microsoft.com/dataset/sentinel-1-rtc
- Sentinel-2 L2A scene classifications, August 23 / September 29 / October 7, with July 14 context. Earth Search STAC, Copernicus data. Exact scene IDs remain in the prior radar methods and acquisition snapshots.
- ESA WorldCover 2021 v200, historical class map, CC BY 4.0. © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021). https://esa-worldcover.org/en/data-access
- Copernicus DEM GLO-30 DSM, EGM2008 elevations. Source URL and hash in data/derived/terrain.json. Contains modified Copernicus DEM data. Terms https://registry.opendata.aws/copernicus-dem/
- Geoscience Australia DEA Landsat Water Observations, ga_ls_wo_3. Referenced label products remain documented in provenance manifests and the negative/uncertain prior evaluation. https://knowledge.dea.ga.gov.au/notebooks/DEA_products/DEA_Water_Observations/

## Models and contextual research

DODOC and BRAT are cited prior art. No third-party implementation is vendored. BRAT's catalog lists no license; its code is not redistributed. The educational solver is original project code using documented oxygen-budget relationships. Menindee 2023 is historical context from NSW EPA, with no event imagery copied into the app.

MIT applies to project code only. External data and research retain their own rights. AI-assisted implementation and report authorship are disclosed in AI_DISCLOSURE.md.

## Flood-budget upgrade sources

Gibbs, Wallace & Mosley (2022), DOI https://doi.org/10.1002/hyp.14529, Table 1 supplies nine published sensitivity ranges. The PDF is linked and hashed rather than redistributed. The pinned flowmatters/dodoc-source commit, reviewed formulas and no-declared-license status are in data/provenance/flood_parameters.json. No DODOC source code is vendored. External authors retain their rights. These published facts/methods do not imply endorsement or new site calibration.

Four additional original DEW daily source responses for A4261023/A4261024 oxygen and temperature are retained with exact request URLs and SHA-256 in flood_context_manifest.json. Excluded grades are preserved. Discharge availability queries at seven selected stations are documented; no study-period local discharge was found in those returned datasets. The regional October 9 flow report is separately linked/hashed in regional_flow_context.json and is not treated as local model forcing. DEA candidate water support is recomputed from the previously verified raster hashes and source timestamps; reference-date mismatch remains explicit.

Six original field-visit JSON responses are retained and verified against field_visit_manifest.json; they preserve exact instantaneous timestamps, station datums, quality and source URLs. NISAR metadata is rechecked by scripts/recheck_nisar_catalog.py, with source URLs and matches in nisar_metadata_recheck.json.

## Essentiality audit (0.3)

No new satellite or water-quality observation was synthesized or acquired for the structural ablation. Retained source snapshots supply the same dates/locations/quality. NISAR contributes HHHH/HVHV absolute power and changes; HH-minus-HV is a derived log-power contrast, not a verified flooding index. Conventional observation timestamps in the new dossier are selected from the retained STAC/DEA manifests, using the actual Sentinel-2 platform used in the mosaic. data/provenance/essentiality_protocol.json explains the initial pre-execution audit and the later machine-readable record; there is no external preregistration. Complete arm and model-audit outputs are in data/derived/nisar_ablation.json and model_audit_03.json. All original third-party data and literature rights remain unchanged.

## Case-studies candidate (0.4)
- NASA/ISRO NISAR L2 GUNW provisional P05023 v1.0.11 (ASF DAAC), stack 047 ascending frame 015, 12-day pairs 2026-08-16/08-28, 2026-09-21/10-03 and 2026-10-03/10-15; used as phase values at gauge locations (derived values only are shipped).
- USGS EDEN: 2026 gauge coordinates and subareas (doi:10.5066/P13BBYUJ) and EDEN observed daily water-level series for WCA-3A marsh gauges (USGS and SFWMD stations). USGS data are public domain; SFWMD data are as published through EDEN.
- Louisiana CPRA CIMS discrete water-quality profiles, stations SWMP0201-SWMP0205, six monthly visits January-June 2026 (summary ranges only).
- Derived file data/derived/case_studies.json is built by scripts/build_case_studies.py from private research outputs with recorded SHA-256 values; raw radar and gauge files are not redistributed.
