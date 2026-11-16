## O2tracker - exploring wetland change with NISAR

### Summary

Fish need dissolved oxygen to survive, but when oxygen levels drop, aquatic life can suffocate, threatening entire ecosystems, fisheries, and the communities that depend on them. O2tracker explores how NASA's NISAR satellite radar can help scientists better understand changing wetland conditions that influence water quality. Our interactive platform allows users to compare real satellite observations, identify and measure environmental changes, and examine water-level data. We also highlight real low-oxygen measurements from Louisiana to demonstrate why protecting aquatic ecosystems matters. In an exploratory Florida Everglades experiment, incorporating NISAR reduced water-level estimation error from 3.43 to 2.31 cm. It provides valuable environmental evidence that could help researchers identify areas needing further investigation. Our long-term vision is to support earlier detection of environmental risks, better water-quality monitoring, and more informed decisions that protect aquatic life, fisheries, and the people who rely on healthy waterways.

### [Project Demonstration](https://drive.google.com/file/d/1YiBnBPNBJXRNtwNCPkszemgqDcOdPZ9X/view?usp=sharing)

## Detailed Description

O2tracker is an interactive wetland-change exploration platform that brings NASA-ISRO NISAR radar observations together with independent field measurements. It helps users investigate how wetland surfaces change over time, compare satellite evidence with water-level observations, and understand what those measurements can tell us about the landscape.

The application combines two radar study areas: the Katarapko-Pike floodplain in South Australia and Water Conservation Area 3A in the Florida Everglades. Through an interactive viewer, users can compare acquisitions, switch radar layers, inspect pixel values and coordinates, and examine the evidence behind an exploratory water-level experiment. Separate Louisiana field measurements and an educational oxygen-budget investigation connect the work to questions about wetland health.

## How It Works - Key Technical Features

1. **Real NISAR radar exploration**: We use three GCOV acquisitions over Katarapko-Pike, dated August 23, September 28, and October 10, 2026. Users switch between HH and HV polarization, inspect dated backscatter values, and see where independent river oxygen stations are located. Acquisition dates, units, processing information, and source identifiers remain visible.
2. **Interactive before-and-after comparison**: A movable divider and difference view reveal how radar backscatter changes between acquisitions. Comparisons use aligned data from the same track and frame. The calculation is based on the change in returned radar power: Backscatter change (dB) = 10 log₁₀(Pafter / Pbefore). The same polarization and aligned valid pixels are required. A backscatter change alone does not establish flooding.
3. **Interferometric wetland observations**: The Everglades viewer displays coherence and unwrapped phase from eight 12-day NISAR GUNW pairs. Coherence describes how similar the radar signal remains between passes; phase contains relative path-length information. Gauge locations and observations help users investigate how these signals relate to wetland water-level change.
4. **Independent withheld-gauge testing**: The Evidence view compares water-level-change estimates from the remaining gauges alone with estimates assisted by NISAR phase. Each test excludes the target gauge from phase referencing and sign calibration. This makes the contribution of the radar information directly comparable with the gauge-only methods tested.
5. **Educational oxygen-budget investigation**: The earlier Katarapko investigation lets users change assumed floodplain area, water depth, flow, and connectivity, then explore a 512-member oxygen-budget ensemble, uncertainty, and sensitivity. A remove-the-satellite control shows which outputs depend on radar. In the current model, the retained evidence arms produce identical oxygen outputs because NISAR constrains no physical oxygen-model parameter.

## Benefits and Goals
O2tracker makes technical radar evidence easier to explore through maps, date controls, pixel inspection, and linked charts. Its central goal is to help users move from seeing a change to asking what physical evidence would explain it.

1. **For students and educators**: Explore polarization, backscatter, coherence, and phase through actual satellite observations.
2. **For wetland researchers**: Inspect the relationship between radar evidence and independent gauges, including baseline errors and failed replication attempts.
3. **For resource managers and the public**: Understand the evidence behind a result and identify the additional measurements needed before drawing management conclusions.

Observed, Derived, Modeled, and Exploratory labels distinguish direct measurements from computed estimates and educational scenarios. The intended benefit is more accessible, transparent interpretation of Earth observations; operational decision improvements remain a future evaluation goal.

## Presenting NISAR Results

### Everglades Water-Level Change - Exploratory Case Study

We evaluated three ascending interferometric pairs using 33 withheld-gauge tests involving 15 distinct gauges. The strongest gauge-only baseline we tested was multiquadric radial-basis interpolation.

1. **Gauge-only baseline**: Pooled root-mean-square error of 3.43 cm.
2. **NISAR-assisted estimate**: Pooled root-mean-square error of 2.31 cm.
3. **Measured difference in this experiment**: A 32.6% reduction in RMSE relative to that baseline.

A shuffled-phase control did not reproduce the improvement. The result suggests that NISAR phase may add useful spatial information to gauge observations in this setting.

The experiment remains exploratory: only three of eight candidate pairs passed the eligibility gate, the gauge-level 95% interval for mean absolute-error improvement spans −0.37 to 1.50 cm, and a descending-orbit replication could not be scored because too few coherent, eligible gauges were available. The comparison does not establish improvement over operational USGS EDEN water surfaces or a generally validated retrieval method.

## Connecting Surface Change to Wetland Health

### Independent Oxygen Measurements

The Why it matters view presents Louisiana CPRA field-probe profiles from the Maurepas area. The retained measurements include a minimum dissolved-oxygen concentration of 0.89 mg/L at station SWMP0204 on June 1, 2026. Four of the five stations had a profile minimum below 2 mg/L that day. These monthly daytime observations illustrate why wetland monitoring matters, while leaving event duration and ecological effects unresolved.

These oxygen measurements come from a different location and dataset than the Everglades experiment. At the original South Australian sites, 53 GOOD-grade daily oxygen means per station were all above 8 mg/L, and only three independent radar dates were available. 

## Tools, Development, and Scientific Transparency

1. **Application and numerical analysis**: Python, FastAPI, NumPy, and SciPy support the API, comparisons, and educational models.
2. **Geospatial data processing**: Rasterio, PyProj, h5py, and Shapely support raster reading, coordinate handling, and spatial analysis. NASA Earthdata and Harmony support NISAR discovery and subsetting.
3. **Interactive presentation**: HTML, CSS, and JavaScript use Canvas for raster exploration and SVG for charts, with keyboard controls and responsive layouts.
4. **Traceable display assets**: Compact value-encoded raster images retain coordinate transforms, units, and file hashes in a manifest. South Australian 20 m power data are averaged onto a 40 m display grid before conversion to decibels; Everglades phase and coherence are displayed on an 80 m grid. Pixel readouts are approximate because display values are quantized.

The supplied application snapshot runs without Earthdata credentials. Rebuilding the complete analysis from raw observations requires external files and access. Methods, source acknowledgments, SI assistance, and limitations are documented alongside the project. Our creative contribution is the combination of interactive radar exploration with visible evidence checks, including withheld observations, comparison baselines, placebo results, and sensor removal.

## Strategic Roadmap and Future Applications

1. **Expand the radar time series**: Add independent acquisitions and study periods to test whether the observed patterns persist across changing conditions.
2. **Replicate the hydrology experiment**: Evaluate additional wetland sites and orbit geometries, and compare against appropriate operational products.
3. **Connect the missing field evidence**: Collect matched inundation, outlet discharge, carbon, and subdaily oxygen observations to investigate the pathway from landscape wetness to water quality.
4. **Evaluate practical use**: Test the interface with educators, researchers, and wetland managers, and assess whether it improves interpretation and the design of follow-up observations.

O2tracker addresses Dancing with the SARs by turning NISAR observations into an interactive account of wetland surface change. Its longer-term vision is to make satellite and field evidence easier to examine together, with the uncertainty and validation needs visible at every stage.

## License

Project code uses the MIT license. External datasets retain their original rights and attribution; see [DATA_SOURCES.md](DATA_SOURCES.md).

Portions of this repository are generated with assistance of LLM's from providers such as OpenAI and Anthropic; see [AI_DISCLOSURE.md](AI_DISCLOSURE.md).
