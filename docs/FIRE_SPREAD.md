# Fire spread: what ships, and what it would take to train the rest

`pyragrid_system_design.md` §3 specifies a hybrid: a physics model and a learned model,
reconciled. That document calls `from rothermel import FireSpreadModel` but never implements
it, so the physics half was the missing piece. It is now implemented, calibrated and tested.
The learned half is not built, and this document is explicit about the gap rather than
papering over it.

## What ships today

`backend/app/spread.py`, exposed as `GET /api/sites/{site_id}/forecast?at=`.

| Component | Source | Status |
|:--|:--|:--|
| Surface rate of spread | Rothermel (1972) | Implemented, with Albini (1976) dead/live weighting |
| Fine fuel moisture from temperature and RH | Simard (1968) | Implemented |
| Directional spread (heading, flank, backing) | Alexander (1985) ellipse, Anderson (1983) length-to-breadth | Implemented |
| Fuel models | Anderson (1982) FM1, FM2, FM4, FM5 | Calibrated to published Table 1 rates |
| Time to arrival at a site | distance ÷ directional rate | Implemented |
| Front position at +1/3/6/12 h | as above | Implemented |
| Learned correction / PINN / transformer | design doc §3.2, §4 | **Not built** |
| Calibration against observed perimeters | — | **Not done** |

**Calibration is explicit.** The implementation reproduces FM1 within 4% of its published
rate unaided, but under-predicts the live-fuel models by roughly half, because a full
multi-class live fuel treatment with dynamic live moisture of extinction is more than was
built here. Each fuel model therefore carries a `calibration` factor pinning it to
Anderson's published rate at the benchmark condition (5 mph midflame wind, 8% dead fine
moisture, no slope). `tests/test_spread.py` asserts every model stays within 10% of its
published value, so a coefficient edit cannot silently drift.

| Fuel class | Anderson model | Published | Implementation |
|:--|:--|--:|--:|
| low | FM1 short grass | 78 ch/h | 78.0 |
| medium | FM2 grass and scattered timber | 35 ch/h | 35.1 |
| high | FM5 brush and shrub | 18 ch/h | 17.9 |
| very_high | FM4 heavy chaparral | 75 ch/h | 75.0 |

Under the demo's conditions (20 km/h wind, 32 °C, 22% RH, 15% slope) that gives heading
rates of 4.5 km/h in grass down to 0.6 km/h in brush — the right order of magnitude for
observed Mediterranean fire behaviour.

### How the advisor uses it

The forecast is added to the advisor's context and gains three citable evidence keys:
`forecast:time_to_arrival`, `forecast:spread_rate`, `forecast:direction`. The system prompt
instructs the model to sequence suggestions inside the arrival window, to quote the
forecast's numbers rather than inventing its own, and never to contradict
`arrival_confidence`. The template engine produces the same forecast-driven suggestion when
no model is available, so the capability does not depend on the LLM.

This is the one place the product answers "when", not just "how bad".

## What it does not do

- No learned component and no calibration against observed fire perimeters.
- Anchors the front on the **nearest VIIRS detection**, because VIIRS gives detections, not
  perimeters. A 375 m pixel is the resolution floor on every distance it reports.
- Uniform slope (`config.ASSUMED_SLOPE_PCT`), because no DEM is loaded.
- Uniform fuel along the whole approach — no fuel map, no fuel breaks, no roads or rivers.
- Constant wind over the forecast window, and no wind field: one wind for the whole site.
- Surface fire only: no crown fire, no spotting, no firebrand transport, which is how fires
  actually cross barriers and jump ahead of the front.
- Live fuel moisture is a seasonal constant (90%), not measured.

Every one of these is returned in the response's `assumptions` array and must be shown
wherever the forecast is displayed.

## Data sources for training the learned half

The design doc lists FEDS, WildfireDB, FRAP and GlobFire. Those are US-centric apart from
FEDS. Below is what is actually needed for this product's two regions — Spain and Tunisia —
plus the sources that carry **spread labels**, which is the part most fire datasets lack.

### Fire perimeters and spread behaviour (the labels)

| Source | Why it matters here | Access |
|:--|:--|:--|
| **Global Fire Atlas** | Per-fire ignition point, **daily spread rate and direction**, size, duration, 2003–2016. This is the closest thing to a ready-made label set for what our model predicts. | globalfiredata.org |
| **EFFIS / GWIS** (Copernicus JRC) | Daily burnt-area perimeters for Europe **and North Africa** — the only operational source covering both Galicia and Tunisia. | effis.jrc.ec.europa.eu, gwis.jrc.ec.europa.eu |
| **Copernicus EMS Rapid Mapping** | Hand-delineated vector perimeters, often multiple per fire, for major Mediterranean events. Small in number, very high quality. | emergency.copernicus.eu |
| **FEDS** (design doc) | Global 375 m half-daily fire event perimeters, 2012–2023. Primary training set as the doc says. | figshare.com |
| **ESA FireCCI51** | Climate-quality global burned area, 250 m, 2001–2020, consistent across regions. | climate.esa.int |
| **NASA FIRMS archive** | Full VIIRS/MODIS active-fire history. We already ingest the live product; the archive gives the time series. | firms.modaps.eosdis.nasa.gov |
| **MTBS**, **California FRAP** | Long US severity and perimeter history. Useful for pre-training volume, wrong fuels for our regions. | mtbs.gov, data.ca.gov |

### Weather and fire-weather

| Source | Why | Access |
|:--|:--|:--|
| **ERA5 / ERA5-Land** | Reanalysis wind, temperature, RH, soil moisture. The standard training covariate. | cds.climate.copernicus.eu |
| **CAMS GFAS** | Fire radiative power assimilation — intensity, not just location. | atmosphere.copernicus.eu |
| **EFFIS fire danger (FWI)** | Daily Canadian FWI components for Europe and North Africa. | effis.jrc.ec.europa.eu |
| **AEMET OpenData** | Real Spanish station observations for the Galicia region. | opendata.aemet.es |
| **INM Tunisia** | Tunisian national meteorology; station data for the northwest. | meteo.tn |
| **Open-Meteo** | What we use now: free, global, real-time, no auth. | open-meteo.com |

### Fuel, terrain and moisture

| Source | Why | Access |
|:--|:--|:--|
| **ESA WorldCover** | 10 m global land cover — works for Tunisia, where CORINE does not reach. | esa-worldcover.org |
| **CORINE Land Cover** | 100 m European land cover, finer fuel classes for Spain. | land.copernicus.eu |
| **JRC European fuel map** | Land cover already translated into fire-behaviour fuel types. | joint-research-centre.ec.europa.eu |
| **Copernicus DEM GLO-30** | 30 m global elevation — replaces `ASSUMED_SLOPE_PCT` with real slope and aspect. Highest-value single addition. | dataspace.copernicus.eu |
| **Globe-LFMC 2.0** | Field-measured live fuel moisture, thousands of samples — replaces our 90% constant. | scientificdata (Nature) |
| **MODIS / Sentinel-2 NDVI, NDMI** | Vegetation dryness in the weeks before a fire. | dataspace.copernicus.eu |
| **Scott & Burgan (2005) 40 fuel models** | Finer fuel parameterisation than Anderson's 13, including Mediterranean shrub types. | USFS RMRS-GTR-153 |

### Highest value first

If only three things are added, these are the three:

1. **Copernicus DEM GLO-30** — removes the uniform-slope assumption. Slope enters Rothermel
   squared, so it is the largest single error term right now, and it needs no training.
2. **EFFIS perimeters for Galicia and Tunisia** — the only way to check whether any of this
   is right in *our* regions. Validation before learning.
3. **Global Fire Atlas** — gives spread rate and direction labels directly, so a learned
   residual becomes a tractable supervised problem instead of a research project.

## Path to the learned model

Ordered by what each step buys, with honest effort:

1. **Validate the physics against EFFIS perimeters** (~1 week). Take the 2025 Galician and
   Tunisian fires, run the forecast from each satellite pass, compare predicted arrival with
   the observed perimeter's next position. Produces the first real error distribution.
   Without this number, nothing below is meaningful.
2. **Add the DEM and a fuel map** (~1 week). Real slope, aspect and fuel per cell along the
   approach, replacing two assumptions with data.
3. **Learn a residual, not a replacement** (~3–4 weeks). Gradient boosting on
   `(observed rate − Rothermel rate)` against weather, terrain and fuel features from the
   Global Fire Atlas. Small, interpretable, and it degrades to the physics model when the
   correction is unavailable — which matters, because the fallback architecture already
   exists.
4. **Only then** the design doc's PINN and spatial transformer (§3.2, §4), which need a
   gridded perimeter-evolution dataset and GPU training. Weeks to months, and step 3 should
   prove the residual is learnable first.

Steps 1 and 2 need no GPU and no training. Step 3 is where compute starts to matter.

## References

- Rothermel, R. (1972). *A mathematical model for predicting fire spread in wildland fuels.*
  USDA Forest Service RP-INT-115.
- Albini, F. (1976). *Estimating wildfire behavior and effects.* USDA GTR-INT-30.
- Anderson, H. (1982). *Aids to determining fuel models for estimating fire behavior.*
  USDA GTR-INT-122.
- Anderson, H. (1983). *Predicting wind-driven wildland fire size and shape.* RP-INT-305.
- Simard, A. (1968). *The moisture content of forest fuels.* Canadian Forestry Service.
- Alexander, M. (1985). *Estimating the length-to-breadth ratio of elliptical forest fire
  patterns.* Proc. 8th Conference on Fire and Forest Meteorology.
- Andrews, P. (2018). *The Rothermel surface fire spread model and associated developments:
  a comprehensive explanation.* USDA RMRS-GTR-371.
