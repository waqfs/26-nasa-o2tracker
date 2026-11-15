# O2tracker website: complete functional overview

This document describes, in full, what the O2tracker website is, what each page and control does, what data it uses, what it found, what it does not claim. All numbers below come from the project's own data files (`data/derived/viewer/manifest.json`, `data/derived/case_studies.json`) and were checked against the running application.

---

## 1. One-paragraph summary

O2tracker is an interactive web application built on real observations from NISAR, the joint NASA/ISRO L-band synthetic aperture radar satellite. It lets anyone look at real radar images of two wetland and floodplain sites, compare dates, read the exact value the satellite measured at any pixel, and now select an area to measure how much it changed, both on its own and compared with the whole scene or with a reference area the user chooses. It also presents one exploratory experiment from the Florida Everglades, in which adding NISAR radar phase reduced the error of water-level-change estimates between ground gauges, and it shows field measurements of low dissolved oxygen in Louisiana as context for why wetland monitoring matters. It is explicitly not an oxygen sensor, not a flood detector and not a warning system. It is a tool for exploring real radar evidence carefully, with its limits shown.

## 2. The problem it addresses

- Wetlands and floodplains change constantly: water rises and falls under vegetation, soils wet and dry, and these changes affect habitat, flooding and water quality (including dissolved oxygen, which fish and other aquatic life need).
- Ground sensors (water-level gauges, oxygen probes) are sparse. Most of a wetland is never measured directly.
- Optical satellites (cameras) are blocked by cloud and darkness and cannot see under vegetation well.
- NISAR is a radar: it sends its own microwave pulses (L-band, wavelength about 24 cm) and measures the echo, so it works day and night and through cloud, and L-band partly penetrates vegetation. NISAR data products are new (provisional products in 2026) and hard to open without specialist software.
- The project's question is therefore: can real NISAR observations be made understandable and useful to researchers, and where does radar actually add information that ground sensors alone cannot provide?

## 3. Key concepts

- **Backscatter (dB):** how much of the radar pulse returns to the satellite. Brighter means more energy returned. It depends on surface roughness, vegetation structure and moisture/water. Measured in decibels; typical values in this scene range from about −25 dB (dark) to −3 dB (bright). More negative means less energy returned.
- **HH and HV:** two polarizations. HH = sent and received horizontally; HV = sent horizontally, received vertically. They respond differently to vegetation and surfaces.
- **Change in backscatter:** the After value minus the Before value. A change is a clue that something about the surface changed. It is not by itself proof of flooding.
- **Coherence (0 to 1):** how similar the radar echo stayed between two passes 12 days apart. High = stable surface; low = changed or noisy.
- **Unwrapped phase (radians):** records tiny path-length changes along the radar's line of sight between two passes. One full cycle (2π) is about 11.9 cm of path change. Over a wetland it can relate to water-level change, but only after calibration.
- **Status labels used throughout the site:** **Observed** (measured directly by the satellite or a field instrument), **Derived** (computed from measurements, such as a difference between dates), **Modeled** (output of an explicit model), **Exploratory** (a finding that still needs independent replication).

## 4. Data used

### 4.1 Katarapko–Pike floodplain, River Murray, South Australia

- NISAR Level-2 GCOV backscatter product (provisional P05023), track 153 ascending, frame 160.
- Three processed acquisitions on the same orbit and an identical grid: **23 August 2026, 28 September 2026 and 10 October 2026** (each at 20:34 UTC).
- HH and HV layers. Source pixels 20 m; displayed at 40 m. Grid EPSG:32754 (UTM zone 54 south).
- The acquisition timeline also shows passes that exist in the NASA archive but were not processed for this release, and gaps where no acquisition exists.
- Two river oxygen monitoring stations from the South Australian Department for Environment and Water are marked on the map (their oxygen records are used in a separate, earlier investigation page).
- Known caveat stored with the data: reference targets elsewhere in the scene also changed between dates, so a common radiometric shift (a whole-image calibration offset) cannot be ruled out.

### 4.2 Everglades Water Conservation Area 3A, Florida

- NISAR GUNW interferometric products, track 47 ascending, eight 12-day pairs (August to October 2026). Displayed at 80 m.
- Layers: coherence and unwrapped phase (relative to the scene median, no atmospheric or tide correction).
- USGS EDEN (Everglades Depth Estimation Network) water-level gauges, with their measured water levels.

### 4.3 Maurepas Swamp / Lake Maurepas, Louisiana

- Louisiana CPRA (Coastal Protection and Restoration Authority) discrete water-quality profiles at stations SWMP0201 to SWMP0205, January to June 2026: 30 field profiles, monthly daytime visits.
- This is a different site from the radar data. It is field context only; the satellite did not observe it.

## 5. Site structure

The application is a FastAPI backend serving a buildless (no JavaScript build step) frontend.

| Address | What it is |
|---|---|
| `/` | **Landing page**: the front door of the site. |
| `/app` or `/app#explore` | **Radar viewer** (the main tool). |
| `/app#evidence` | **Everglades test (E15)**: the water-level experiment. |
| `/app#context` | **Louisiana oxygen data**: field context. |
| `/app#about` | **Methods & sources**. |
| `/investigation` | The original Katarapko–Pike investigation from earlier releases (radar plus river-oxygen sensors plus an educational oxygen-budget model). |

The top bar is a dark strip with the O2tracker wordmark and five links: Home, Radar viewer, Everglades test (E15), Louisiana oxygen data, Methods & sources. The wordmark and Home return to the landing page from every page, including the earlier investigation page. Every button and link on the landing page leads into the matching section of the app.

## 6. The Radar viewer in detail (main page)

### 6.1 Layout

- Left/centre: a large map canvas showing the radar image, with a date label in each top corner, a scale bar bottom-left, and map tools bottom-right (**Select area**, **+**, **−**, **Fit**).
- Directly under the map: a slider that positions the before/after divider, then the **area analysis panel** (new; see section 7), then the colour legend and the acquisition timeline.
- Right column (the inspector): a one-line description of the layer, Layer choice, View choice, Before and After date pickers, a toggle to show monitoring stations, the pixel readout, product metadata, an expandable "Full provenance" section, and a caveat.
- Site switch at the top: **Katarapko–Pike** or **Everglades**.
- On phones the map comes first, then the area panel, then the controls.

### 6.2 What a user can do

- **Pan** by dragging, **zoom** with the scroll wheel or + / −, **Fit** to reset.
- **Compare dates (Katarapko):** View = Before / after shows the Before date on the left of a vertical divider and the After date on the right. Drag the divider (or the slider under the map) to wipe between the two dates. View = Difference shows After minus Before as a blue (decrease) to orange (increase) colour map, ±6 dB. View = Single date shows one acquisition.
- **Pick dates:** with the Before/After dropdowns, or by clicking a date on the timeline (it moves whichever end of the comparison is nearer).
- **Switch polarization:** HH or HV.
- **Inspect a pixel:** click anywhere. The inspector shows the value on every date for that pixel, the change between the chosen dates, latitude/longitude and UTM coordinates, and the precision of the displayed value. Clicking a station marker also shows its name.
- **Everglades:** choose Coherence or Phase and a 12-day pair on the timeline. Gauge markers show which gauges were scored in the E15 experiment; clicking a gauge shows its measured 12-day water-level change and the NISAR-assisted and gauge-only estimates.
- **Keyboard:** arrows pan, + / − zoom, 0 fits, Enter inspects the centre.

## 7. Area analysis (added in the latest work)

This feature answers the criticism that the site "only visualizes data." It turns the viewer into a measuring instrument.

### 7.1 What it does

Available on the Katarapko–Pike site in Before/after and Difference views (the two views that compare dates).

1. **Starting box.** When the page opens, a blue box is already drawn on the map: the 48 × 48 pixel block (about 1.9 km across) with the largest average change in the whole scene for the current layer and dates, kept away from the image edges. So the first thing anyone sees is a real result, not an empty tool. The panel states that this is the strongest block in the scene (a selected maximum, not a typical area).
2. **Three large numbers** in a panel under the map:
   - **This area:** the median change (After minus Before) of all valid pixels inside the box, in dB.
   - **Whole scene:** the same median over the entire image. This shows how much the scene as a whole shifted between the dates.
   - **Area minus scene:** the difference between the two, showing how much more (or less) this area changed than the scene overall.
3. **A detail line:** layer, the two dates, number of valid pixels, and the spread (the middle half of pixel changes, from the 25th to the 75th percentile).
4. **A trajectory chart across all three dates:** the box's median backscatter level on 23 Aug, 28 Sep and 10 Oct (solid blue line with a soft gradient fill) against the whole scene's level (dashed grey line), with the currently compared dates emphasized. It shows whether a change continues, reverses or levels off.
5. **Select area (draw your own box):** the Select area button on the map toolbar turns drawing on. Drag on the map to draw a box; drag inside it to move it; drag its edges or corners to resize it. Numbers and chart update live while dragging. The before/after divider always takes priority over the box, and a simple click still inspects a single pixel.
6. **Use as reference:** turns the current box into a dashed orange "Reference" box. The user then draws the area they want to study. All comparisons switch from the whole scene to the reference: the second number becomes "Reference area", the third becomes "Area minus reference", and the chart's dashed line becomes the reference's trajectory. This is the standard way a researcher checks whether a change is local or a calibration/whole-image shift: compare against ground believed not to have changed. "Clear reference" returns to whole-scene comparison.
7. **Download report** as JSON or CSV. The JSON contains: the box in pixel and UTM coordinates, layer, both dates with granule IDs and source file SHA-256 hashes, the three numbers, the spread, pixel counts (valid, excluded, at clip limits), the reference box and its statistics if set, the three-date trajectory, a histogram of pixel changes, the measurement precision (±0.12 dB for a change), how the box was chosen, the data caveat, and the statement: "A candidate to check in the field or with other data, not a finding. A radar backscatter change is not by itself a flooding change, and this is not an oxygen measurement."
8. **Keyboard:** B creates a box or toggles select mode; Shift + arrows move the box; Shift + Alt + arrows resize it; Delete clears it; Esc leaves select mode.
9. **Everglades:** the numbers are replaced by one line explaining that area change needs two backscatter dates of the same ground, which the Katarapko–Pike site has.

### 7.2 Example values (HH polarization, 23 Aug to 28 Sep 2026, starting box)

- This area −3.6 dB, Whole scene −1.6 dB, Area minus scene −2.0 dB; 2,304 valid pixels; middle half −5.0 to −2.4 dB.
- Trajectory (median level): this area −14.16, −18.12, −18.12 dB; whole scene −14.04, −16.20, −16.08 dB on 23 Aug, 28 Sep, 10 Oct. In words: the area's backscatter fell about 4 dB by 28 September and stayed down on 10 October, while the scene as a whole fell about 2 dB.
- Interpretation that is allowed: this area's radar return dropped more than the scene's and stayed low, which makes it a candidate for a closer look. Interpretation that is not allowed: that it flooded, or anything about oxygen.

### 7.3 How the numbers are computed (and verified)

- Computed entirely in the browser from the same value-encoded radar images the viewer displays (8-bit codes with a stored offset and scale of 0.12 dB per step).
- Changes are computed exactly on the integer codes, and medians come from histograms, so the numbers update instantly while dragging and are exact for the encoded data.
- Pixels with no data on either date are excluded; boxes with fewer than 25 valid pixels show "Too few valid pixels".
- Every number (starting box, drawn, moved and resized boxes, both polarizations, different dates, Difference view, trajectory, reference box) was checked against an independent Python/NumPy recomputation from the original image files; all matched.

### 7.4 Limitations

- "Whole scene" is the median change of the entire image, not a calibrated radiometric correction. It may itself contain real widespread change (rain, soil moisture, flooding), so subtracting it can hide real change. The reference box exists to make a more deliberate comparison.
- The trajectory chart shows the median level on each date, while the big numbers show the median of per-pixel change; the two can differ slightly.
- Precision: about ±0.12 dB for a change, from the 8-bit display encoding.
- Neighbouring pixels are correlated, so pixel counts are not independent samples.

## 8. Everglades test (E15) page

- **Question:** can NISAR radar phase improve estimates of water-level change between gauges in a marsh?
- **Method:** each marsh gauge is withheld in turn. Its 12-day water-level change is estimated two ways: (1) from the other gauges alone, using the strongest gauge-only interpolation tested (a radial-basis function), and (2) with NISAR interferometric phase calibrated by those same other gauges. Both estimates are compared with what the withheld gauge actually measured.
- **Result (Table 1 on the page):** pooled RMSE **2.31 cm with NISAR** vs **3.43 cm gauge-only**, about **33% lower error**, across **33 withheld-gauge cases** in **3 ascending radar pairs** (track 47, August to October 2026).
- **Stated right next to the result:** the gauge-level 95% interval of the improvement is **−0.37 to 1.50 cm and includes zero**.
- **Figure 1:** scatter of estimated vs measured change; each gauge's two estimates are joined by a thin vertical line so the closer one is visible; a dashed line marks perfect agreement; filter by radar pair. Hover or tap shows values in a readout line.
- **Figure 2:** error by radar pair (bars): 3.24 vs 4.45 cm, 1.99 vs 2.99 cm, 1.56 vs 2.79 cm, all pairs 2.31 vs 3.43 cm.
- **Controls and limitations:**
  - Placebo: shuffling phase values among gauges (1,000 times per pair) removed the improvement (shuffled error about 7.1, 5.2, 7.1 cm vs 3.2, 2.0, 1.6 cm with real phase).
  - Replication: the descending orbit (track 170) could not be scored (no pair had eight coherent, eligible gauges), so the result is single-geometry and not yet replicated.
  - Baseline: the comparison is against a gauge-only interpolation, not the operational USGS EDEN water-surface product.
  - Phase is referenced and its sign set by the training gauges: a gauge-calibrated estimate, not a stand-alone retrieval.
  - Daily-mean gauge stage is compared with a morning satellite pass; the NISAR product is provisional.
  - No oxygen, discharge or ecological-risk result follows from this test.
- **Table 2:** all 33 withheld-gauge results.

## 9. Louisiana oxygen data page (context)

- Headline: low dissolved oxygen in Maurepas Swamp, Louisiana (field data), labelled Observed.
- Lowest reading **0.89 mg/L** at SWMP0204 on 1 June 2026; **4 of 5** stations read below 2 mg/L on 1 June 2026; 30 field profiles over six monthly daytime visits.
- Figure 3: one small chart per station showing the range of dissolved oxygen across depths on each visit, with a shaded band below 2 mg/L. Each station's full visit values are available in an expandable list.
- Stated limits: these readings do not show how long low oxygen lasted, what caused it, or any effect on fish; no causal or predictive NISAR-to-oxygen relationship has been established; different site, data and dates from the radar.

## 10. Methods & sources page

- How the status labels are used (Observed, Derived, Modeled, Exploratory).
- What NISAR measures (backscatter, coherence, unwrapped phase), in plain language.
- Data sources: NASA/ISRO NISAR via the NASA Alaska Satellite Facility DAAC (open data); USGS EDEN gauges (doi:10.5066/P13BBYUJ) and observed water levels; Louisiana CPRA CIMS profiles; South Australia Department for Environment and Water records.
- The earlier Katarapko–Pike investigation, including a "remove the satellite" test in which the educational oxygen model produced identical outputs with and without NISAR (NISAR currently constrains no oxygen-model parameter there).
- Links to the science, limitations, data-source, AI-disclosure and reproducibility documents.
- Project history: developed as OXYGEN DEBT, renamed O2tracker.

## 11. Landing page

Served at `/`, the address visitors open first.

- Headline: "Same ground. Five weeks apart. What changed?"
- A live interactive radar scene (the Katarapko–Pike HH images from 23 August and 28 September 2026). The before/after divider sweeps once on load to show it can be dragged. Moving the pointer reads out the measured value on each date and the change, live; clicking pins a spot. It opens pinned on the block with the largest change so real numbers are visible immediately. A toggle switches to a "Show the change" colour map.
- A short explanation band: radar does not take a photo, it measures how the ground answers back; a change in the echo is a clue, not a verdict.
- The Everglades result as a simple dot chart: 3.43 → 2.31 cm, with the 95% interval and replication status stated in the caption.
- A closing section explaining the status labels and a button: "Measure an area yourself", leading into the Radar viewer.

## 12. Visual design

- Light theme throughout (soft grey-blue page background `#f4f6f8`, white panels).
- Typography: IBM Plex Sans for all interface text with tabular figures for numbers; Source Serif 4 for landing-page headlines. No monospace fonts.
- Colour is reserved mainly for data: blue `#1f5fa8` for NISAR and the selected area, orange `#c2620f` for the gauge-only baseline and the reference box, grey for whole-scene comparisons. Radar images are greyscale (backscatter), blue-to-orange (change), cividis (coherence) or blue-to-red (phase).
- Rounded map frame and panels with soft shadows; quick hover feedback on controls. Native radio buttons and dropdowns for choices.
- Accessible: keyboard operation of the map and area tool, skip link, screen-reader labels, reduced-motion support; works at phone width with no sideways scrolling.

## 13. What O2tracker does not claim

- It does not measure, predict or forecast dissolved oxygen or hypoxia.
- It does not detect flooding; a radar backscatter change is not by itself a flooding change.
- It is not an early-warning or operational system, and it does not explain fish deaths.
- The Everglades result is a single exploratory test on one orbit geometry, with a confidence interval that includes zero; it is not replicated and does not outperform the operational EDEN product (which was not compared).
- No relationship between NISAR observations and oxygen has been established.
