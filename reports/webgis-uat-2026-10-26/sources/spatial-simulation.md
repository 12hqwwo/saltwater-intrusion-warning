# Spatial simulation API and advisory map (Phases 1–3)

Three read-only endpoints are available under `/api/v1/workspace/simulation`:

| Endpoint | Result |
| --- | --- |
| `GET /corridor` | `corridor` GeoJSON FeatureCollection, coordinate-bearing `gates`, canal IDs and catalog coverage |
| `GET /timeline` | `items` with monthly station EC, empirical salinity, regime, weather and source provenance |
| `GET /frame?year_month=2024-04&open_below_ec=120&close_above_ec=150` | 35 river segments, 1 and 4 g/L boundaries, wind, and every coordinate-bearing gate's simulated state |

Months must use `YYYY-MM`. Missing months return 404; malformed months,
nonfinite/negative thresholds and `open_below_ec >= close_above_ec` return 422.
Unavailable or invalid source files return 503. PostgreSQL mode requires its
configured database; simulation does not silently switch to snapshot mode.

## Evidence and isolation

The simulation is Tier 2. Responses include `simulation_layer: true`,
`gate_decision_eligible: false`, `actuator_command: null`, and the methodology:

`1D River-Axis IDW & Empirical EC-Salinity Conversion (0.0064 g/L per mS/m)`

Existing workspace and multivariate routes, metrics, policies and research
artifacts are retained. Simulation requests do not write observations, gates,
forecasts or decisions. Historical observations and model evaluation metrics
are not replaced by simulation outputs.

The bundled inputs provide 495 consecutive months, June 1985–August 2026:

- Through December 2023, arithmetic monthly means use the selected MRC
  observations for `MRC_VN_019803` and `MRC_VN_019805`. Original quality flags,
  sample dates and sample counts remain in `boundary_provenance`. Observed
  does not imply independently validated. If a different selected dataset has
  gaps, simulation-only interpolation is explicitly marked `imputed` with
  source months; core observations are unchanged.
- From January 2024, EC and scalar weather drivers come from
  `data/models/future_ec_forecast_2024_2026.csv`. The requested regime label
  `ML_FORECAST_ERA5` also carries `RETROSPECTIVE_WEATHER_ESTIMATE` provenance;
  these archived estimates are not promoted to validated live forecasts.
  Complete new station-month pairs extend the timeline. Missing future wind
  directions remain unavailable, rather than being invented.
- Historical scalar weather uses hash-checked, unit-verified ERA5 files in
  `data/external/multivariate_weather`. Regional summaries use Mỹ Tho; both
  stations are included in `weather_by_station`.
- Wind components use recorded daily mean speed and dominant direction in
  `data/external/ec_feature_research_20261019/era5_extra_*.json`:
  `u = -speed*sin(direction)`, `v = -speed*cos(direction)`, averaged by month.
  These are labelled proxies, not native hourly ERA5 u10/v10. Scalar speed and
  vector resultant speed are reported separately; directions are meteorological
  bearings *from* which wind blows.

## Geometry and numerical assumptions

`data/biengioi/tien_river_corridor.geojson` uses WGS84 longitude/latitude,
contains the main Tien axis and ten representative canal branches. Each canal
starts on an axis vertex and contains its catalog gate coordinate at
`gate_path_index: 2`. `gate_code`, `gate_coordinate`, `connection_coordinate`
and `parent_river_id` support a frontend barrier animation. Gate frames expose
`canal_particle_intake_enabled: false` for every default frame, including the
legacy `OPEN_INTAKE` state. Canal particles require an explicit, local preview
action in the frontend; they never indicate a gate command.

The geometry is schematic, not a surveyed centerline or verified canal network.
All 27 coordinate-bearing headworks in the supplied local catalog are in the
Tien Giang catalog. Four Dong Thap workspace catalog entries have no coordinates
and are listed as excluded; no upstream gate coordinates or hydraulic links are
fabricated. Catalog verification designations and source URLs are retained,
including catalog entries that share a coordinate.

Geodesic vertex distances are rescaled separately to the requested nominal
anchors: Tân Châu 0 km, Mỹ Tho 125 km, estuary 175 km. Thus Mỹ Tho stays at
exactly 125 km even though the schematic line's measured length differs.
Thirty-five connected five-kilometre segments preserve intermediate vertices.
EC uses inverse-square distance weights from the two bracketing axis anchors;
segment values are evaluated at their midpoints.

The estuary is an **uncalibrated simulation boundary**:

`my_tho_ec * amplification + max(0, my_tho_ec - tan_chau_ec) * 0.4`

Amplification is 6 in February–May and 1.5 otherwise. These explicit scenario
coefficients are not measured tidal forcing or fitted hydrodynamics.
Dry-season segments at or above the closing threshold animate saline upstream
flow; remaining segments animate freshwater downstream flow. Velocity factors
are bounded 0.2–1.5 and are illustrative EC/season proxies, not measured speeds.

Salinity is `round(0.0064 * EC_mS_m, 3)` g/L. This empirical estimate does not
resolve unknown EC temperature correction. Isohalines solve the continuous
profile against unrounded `1/0.0064` and `4/0.0064` EC thresholds. A boundary
outside the simulated range has an explicit status and null coordinate;
its location is never fabricated. Gates project to the nearest main-axis
segment, with distance and unvalidated hydraulic connectivity disclosed.

Global scenario thresholds produce the following states. They do not replace
source-specific legal operation policies or the evidence-based gate evaluator.

| Outside EC | Compatibility state | Advisory code | Color |
| --- | --- | --- | --- |
| `< open_below_ec` | `OPEN_INTAKE` | `ADVISORY_SAFE_INTAKE` | `#10b981` |
| `>= open_below_ec` and `< close_above_ec` | `CAUTION_TRANSITION` | `ADVISORY_CHECK_ONSITE` | `#f59e0b` |
| `>= close_above_ec` | `CLOSED_SALINITY_BARRIER` | `ADVISORY_HIGH_SALINITY_RISK` | `#ef4444` |

Each frame gate retains `simulated_gate_state` and `state_color` for compatibility
and adds `advisory_code`, `advisory_color`, `advisory_label`, and
`human_in_the_loop_Required: true` (including the capital `R`). The exact labels are:

- `Nguồn nước thuận lợi · Có thể xem xét lấy nước`
- `Chớm lợ / Chuyển tiếp · Cần đo kiểm tra tại mũi cống & canh chân triều`
- `Cảnh báo mặn vượt ngưỡng · Khuyến nghị ưu tiên ngăn mặn`

These are advisory indicators. Engineers must check local measurements and tidal
conditions before making an operational decision. No actuator command is produced.

## Phase 2 map and timeline

The observation view includes the 495-month scrubber, play/pause, 1x/2x/4x
playback, and jumps to March 2016, October 2022, April 2024 and the latest month.
Selecting a month displays its station inputs, source regime and weather.
River colors and particles are schematic; gate markers and cards use advisory
labels rather than claiming a physical open/closed state. A selected gate with a
mapped canal permits an explicit illustrative intake preview, disabled by default.

The default dark basemap applies a CSS filter to key-free OpenStreetMap tiles;
the basemap control can restore the standard appearance. CARTO tiles were
rejected after browser inspection showed `API KEY REQUIRED` tiles. This styling
does not change the geographic data or its provenance.

The EC/g/L toggle changes display values only. Salinity remains an empirical
estimate and retains the underlying EC alongside it; API thresholds and stored
observations remain in mS/m. Crop presets are editable scenario pairs:

| Preset | Lower / upper threshold (mS/m) |
| --- | --- |
| Durian | 50 / 80 |
| Citrus (initial UI selection) | 100 / 150 |
| Rice | 120 / 200 |

These illustrative presets are not validated crop safety limits. The API defaults
remain 120 / 150 mS/m. Scrubbing and threshold edits invalidate older requests;
late responses and failures cannot replace the current selection even if abort
is ignored by the server. Playback generations prevent a paused/restarted run
from creating duplicate timers. Playback stops when the view or tab is hidden.

## PostgreSQL RIA2 synchronization

The previously missing `scripts/sync_ria2_to_postgres.py` validates the current
workspace snapshot and its RIA2 provenance. The current snapshot has 50 samples
from five bulletins, including corrected station-specific collection dates;
the older recovery CSV has 40 samples. Default execution is a dry run; `--apply`
performs append-only inserts within one transaction and checks existing
immutable rows for conflicting values. No schema migration is needed.

```powershell
.venv/Scripts/python.exe scripts/sync_ria2_to_postgres.py
.venv/Scripts/python.exe scripts/sync_ria2_to_postgres.py --apply
```

The verified local database contains 2 MRC and 10 RIA2 stations. The selected
RIA2 dataset has 50 observations matching the current workspace snapshot; the
earlier 40-row recovery dataset is retained separately as an immutable artifact.
A repeated apply inserts nothing. All 927 non-RIA2 observations retain their
original fingerprint. RIA2 geometries stay NULL because the source CRS is
unknown. Dataset metadata retains original source rows and bulletin locators.
Date-only reports use midnight solely for database storage, with that limitation
in dataset metadata and source labels; workspace responses preserve `DATE_ONLY`
and return `observed_at: null`. Existing MRC timestamp behavior is unchanged.

## Verification

Run the FastAPI TestClient regression suite with the project's environment:

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py" -v
```

The new tests cover numerical conversion and threshold equality, continuous
segments, axis projection and exact station anchors, dry/wet flow behavior,
isohaline crossings, catalog merging, controlled errors, and unchanged core
responses including multivariate catalog/evaluation. Dry months `2016-03` and
`2024-04` and wet month `2022-10` are exercised in both snapshot and local
PostgreSQL verification. The Phase 1 database checks remain recorded with their original timestamp in
`spatial-simulation-verification.json`; they are not a new Phase 2 database audit.

Phase 2 verification passes all 32 Python tests, including 15 simulation tests.
Assertions cover exact advisory labels/colors, threshold equality and all 495
default frames with 27 gates each requiring human review and no default intake
particles. The formerly failing legacy PostgreSQL test now targets the current
repository's `read_connection`, permits the immutable artifact load, and asserts
HTTP 503 without a snapshot fallback. Production core behavior was not changed
to satisfy that test.

All 17 frontend tests and the Vite production build pass:

```powershell
node --test tests/*.test.mjs frontend/src/features/gate-simulation-draft.test.js
npm --prefix frontend run build
```

Frontend tests cover display conversion, advisory colors, presets, invalid
thresholds, mismatched frames, cancellation, stale results and stale failures.
A regression test exercises scrubbing followed by an invalid threshold edit,
quick jumps while invalid, and recovery with new valid thresholds.

Browser checks on the local PostgreSQL preview verified the four quick jumps,
4x playback/pause, keyboard scrubbing, crop presets, invalid-input blocking,
EC/g/L labels and both basemaps. Gate selection, explicit intake preview and its
reset on frame changes were checked. The dossier handoff selects `GATE_TG_000`,
copies simulated outside EC and matching thresholds, leaves actual field levels,
datum and measurement time blank, and displays SIMULATION / UNVERIFIED without
saving or evaluating. The forecast preview returned a result and the data-quality
view loaded its source records; no browser console errors were observed.

Desktop and 390px responsive layouts were visually checked. The narrow layout
uses an internally scrollable gate card above the timeline. Screenshots are in
`docs/screenshots/phase2-desktop.jpg` and `docs/screenshots/phase2-mobile.jpg`.
The verification JSON records the browser checks separately from automated tests.

## Phase 3 map workspace and verification

Phase 3 adds a compact map HUD, collapsible station list, threshold popover,
dark/satellite/light basemaps, layer toggles and a 300px gate detail drawer.
The station list, drawer and threshold popover start hidden. Earlier Phase 1–2
evidence above and in the verification JSON is retained with its original scope.

The 56px longitudinal profile uses the frame's 35 segment endpoints and midpoints
over the nominal 0–175 km axis. It marks Tân Châu, Mỹ Tho and Cửa Tiểu,
scenario thresholds and available 1/4 g/L fronts. All 27 gates retain exact
chainage positions; vertical lanes and a separate ordered button matrix keep
coincident gates accessible. Profile selection opens the shared map drawer.
Hover is debounced and requests panning without stealing keyboard focus;
explicit activation may focus the drawer. Selection survives frame loading.
EC/g/L remains a display conversion, with empirical salinity identified as such.

A global cardinal spline joins the 35 river segments and canal geometry with
shared anchors. The river ribbon uses 18/10/6px strokes and eight interpolated
pieces per segment with cached styles. Deep Navy applies
`invert(100%) hue-rotate(195deg) saturate(35%) brightness(58%) contrast(115%)`;
satellite applies `brightness(65%) contrast(115%) saturate(85%)` to base tiles.
These presentation changes do not alter the source coordinates or EC evidence.

The canvas engine uses 220 river particles and adaptive wind counts of 220–360
on desktop or 90–140 on mobile. Wind direction follows the supplied components;
river flow remains an illustrative seasonal/EC scenario. Distance-aware trails sample every 0.8px, retain bounded histories of roughly
12px for river and 26px for wind, and draw smooth current heads (0.7px river,
0.45px wind). No measured 60 FPS performance claim has been established.

The Phase 3 Python run passed all 32 tests in 82.873 seconds. All 33 frontend
tests passed (including eight particle, three geometry and five profile tests). The final Vite production build passed in 5.25 seconds after the drawer focus
fix (`workspace-fo1QjDhG.js`); an earlier build passed in 13.14 seconds. The
33 frontend tests preceded that final map-only focus change, which passed a
syntax check and browser verification. Profile DOM tests cover
selection persistence, hover versus activation events and clearing selection;
hover behavior has not yet been independently exercised in the browser.

Browser checks at 1280×720 verified:

- Hidden initial panels; 27 profile ticks and 27 buttons; station list toggle/refit.
- Invalid 200/150 thresholds followed by a wet-season jump clear stale profile
  and advisories; choosing Citrus restores a valid frame.
- Historical March 2016, wet October 2022 (all green), dry April 2024 and latest
  August 2026; layer toggles and dark/satellite/light tiles without tile errors.
- `GATE_TG_000` profile selection, 300px drawer, selection across frame changes,
  clearing selection when gates are hidden, and drawer close button.
- 4x playback wrapping from August 2026 to June 1985, then pausing.
- Dossier handoff copies 26.665879 mS/m and 100/150 thresholds while actual
  measurements remain blank, marked SIMULATION / UNVERIFIED, without saving
  or evaluating.

The 390×844 mobile check found no horizontal overflow. The two-row HUD was
77.8px high; all 27 ticks/buttons were present, with a nine-column button matrix.
The 411px drawer ended at viewport y=410.5, above the dock at y=428.4. Activation
brought the focused drawer into view; closing it returned focus to the
`GATE_TG_000` matrix button. Final browser console errors were empty.

Screenshots `docs/screenshots/phase3-desktop.jpg` and
`docs/screenshots/phase3-mobile.jpg` were captured and visually inspected;
the desktop capture also exercises a 1000×760 breakpoint. Full-page browser
capture was unavailable, so images were assembled from overlapping normal
viewport captures and cropped to the map section, preserving controls and dock.
