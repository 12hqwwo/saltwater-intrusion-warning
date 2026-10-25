"""Read-only Tier 2 river-axis scenarios, separate from verified core evidence.

The axis, estuary boundary, hydraulic links and flow factors are illustrative
simulation assumptions. No result is written to observations or gate policies.
"""
from bisect import bisect_right
import csv
import json
import math
from pathlib import Path

from backend.repositories import workspace as store
from backend.services.spatial_inputs import monthly_inputs
from backend.services.workspace import WorkspaceError, load_bundle

ROOT = Path(__file__).resolve().parents[2]
CORRIDOR_PATH = ROOT / 'data/biengioi/tien_river_corridor.geojson'
GATE_CATALOG = ROOT / 'data/8file/03_sluice_gates_190_and_27_verified_gis.csv'
METHODOLOGY = '1D River-Axis IDW & Empirical EC-Salinity Conversion (0.0064 g/L per mS/m)'
# Axis anchors are orthogonal feet on the cached OSM centerline, not bank pins.
# Keep the station features themselves at their original catalog coordinates.
TAN_CHAU = [105.23607136, 10.80589425]
MY_THO = [106.35984003, 10.34514228]
ESTUARY = [106.7503834, 10.2635303]
GATE_ADVISORIES = {
    'OPEN_INTAKE': ('ADVISORY_SAFE_INTAKE', '#10b981',
                    'Nguồn nước thuận lợi · Có thể xem xét lấy nước'),
    'CAUTION_TRANSITION': ('ADVISORY_CHECK_ONSITE', '#f59e0b',
                           'Chớm lợ / Chuyển tiếp · Cần đo kiểm tra tại mũi cống & canh chân triều'),
    'CLOSED_SALINITY_BARRIER': ('ADVISORY_HIGH_SALINITY_RISK', '#ef4444',
                              'Cảnh báo mặn vượt ngưỡng · Khuyến nghị ưu tiên ngăn mặn'),
}


def _metadata():
    return dict(simulation_layer=True, methodology=METHODOLOGY,
                tier=2, gate_decision_eligible=False, actuator_command=None)


def _nonnegative(value, label):
    if isinstance(value, bool):
        raise ValueError(f'{label} must be a finite nonnegative number.')
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f'{label} must be a finite nonnegative number.')
    return value


def ec_to_salinity_g_l(ec_ms_m: float) -> float:
    """Empirical estimate only; EC is mS/m and the result is g/L."""
    return round(0.0064 * _nonnegative(ec_ms_m, 'EC'), 3)


def gate_state(ec_ms_m, open_below_ec_ms_m=120.0, close_at_or_above_ec_ms_m=150.0):
    ec = _nonnegative(ec_ms_m, 'EC')
    opening = _nonnegative(open_below_ec_ms_m, 'Opening threshold')
    closing = _nonnegative(close_at_or_above_ec_ms_m, 'Closing threshold')
    if opening >= closing:
        raise ValueError('Opening threshold must be less than closing threshold.')
    if ec < opening:
        return 'OPEN_INTAKE'
    if ec >= closing:
        return 'CLOSED_SALINITY_BARRIER'
    return 'CAUTION_TRANSITION'


def _read_corridor():
    try:
        data = json.loads(CORRIDOR_PATH.read_text(encoding='utf-8-sig'))
        main = next(f for f in data['features'] if f['properties']['id'] == 'TIEN_MAIN')
        coordinates = main['geometry']['coordinates']
        if (data['type'] != 'FeatureCollection' or main['geometry']['type'] != 'LineString'
                or len(coordinates) < 3 or MY_THO not in coordinates[1:-1]
                or coordinates[0] != TAN_CHAU or coordinates[-1] != ESTUARY
                or not all(_point(dict(type='Point', coordinates=p)) for p in coordinates)
                or any(a == b for a, b in zip(coordinates, coordinates[1:]))):
            raise ValueError('Invalid simulation corridor.')
        return data, coordinates
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        raise WorkspaceError(503, 'Simulation corridor unavailable or invalid.') from exc


def _point(geometry):
    if not isinstance(geometry, dict) or geometry.get('type') != 'Point':
        return None
    coords = geometry.get('coordinates')
    if not isinstance(coords, (list, tuple)) or len(coords) != 2:
        return None
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in coords):
        return None
    return list(coords) if -180 <= coords[0] <= 180 and -90 <= coords[1] <= 90 else None


def _distance_km(a, b):
    lon1, lat1, lon2, lat2 = map(math.radians, [*a, *b])
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371.0088 * 2 * math.asin(min(1, math.sqrt(h)))


class RiverAxis:
    """Geodesic vertex distances rescaled separately to fixed 0/125/175 anchors."""
    def __init__(self, coordinates):
        self.coordinates = coordinates
        distances = [0.0]
        for a, b in zip(coordinates, coordinates[1:]):
            distances.append(distances[-1] + _distance_km(a, b))
        pivot = distances[coordinates.index(MY_THO)]
        self.chainages = [d / pivot * 125 if d <= pivot else
                          125 + (d - pivot) / (distances[-1] - pivot) * 50 for d in distances]

    def coordinate(self, chainage):
        i = min(len(self.chainages) - 2, max(0, bisect_right(self.chainages, chainage) - 1))
        t = (chainage - self.chainages[i]) / (self.chainages[i + 1] - self.chainages[i])
        a, b = self.coordinates[i:i + 2]
        return [round(a[j] + t * (b[j] - a[j]), 8) for j in range(2)]

    def section(self, start, end):
        return [self.coordinate(start)] + [p for x, p in zip(self.chainages, self.coordinates)
                                         if start < x < end] + [self.coordinate(end)]

    def project(self, coordinate):
        # Local equirectangular projection; suitable for this small regional axis.
        scale_x = 111.195 * math.cos(math.radians(coordinate[1]))
        scale_y = 111.195
        best = None
        for i, (a, b) in enumerate(zip(self.coordinates, self.coordinates[1:])):
            ax, ay = (a[0] - coordinate[0]) * scale_x, (a[1] - coordinate[1]) * scale_y
            dx, dy = (b[0] - a[0]) * scale_x, (b[1] - a[1]) * scale_y
            t = max(0, min(1, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
            distance = math.hypot(ax + t * dx, ay + t * dy)
            chainage = self.chainages[i] + t * (self.chainages[i + 1] - self.chainages[i])
            if best is None or distance < best[0]:
                best = (distance, chainage)
        distance, chainage = best
        return dict(chainage_km=round(chainage, 6), distance_to_axis_km=round(distance, 3),
                    projected_coordinate=self.coordinate(chainage),
                    projection_method='NEAREST_MAIN_AXIS_SEGMENT',
                    hydrological_link_validated=False)


def _catalog_gates(bundle, corridor):
    """Merge only actual supplied coordinates; never create missing gate locations."""
    merged = {}
    try:
        with GATE_CATALOG.open(encoding='utf-8-sig', newline='') as stream:
            for row_number, row in enumerate(csv.DictReader(stream), 2):
                if row['is_verified_27_headworks'].lower() != 'true':
                    continue
                geometry = dict(type='Point', coordinates=[float(row['lon_wgs84']), float(row['lat_wgs84'])])
                if not _point(geometry):
                    raise ValueError('Invalid catalog gate coordinate.')
                merged[row['gate_code']] = dict(
                    gate_code=row['gate_code'], gate_name=row['gate_name'], geometry=geometry,
                    layer_type='SIMULATION_GIS_GATE', location_status=row['location_status'],
                    coordinate_source='LOCAL_GIS_CATALOG',
                    source_locator=f'{GATE_CATALOG.relative_to(ROOT).as_posix()}:row {row_number}',
                    source_reference=row['legal_source_url'], catalog_verification_claim=True,
                    operating_policy_status='SIMULATED_GLOBAL_THRESHOLDS',
                )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise WorkspaceError(503, 'Simulation GIS gate catalog unavailable or invalid.') from exc
    missing_coordinates = []
    for row in bundle['gates']:
        if _point(row.get('geometry')):
            merged[row['gate_code']] = dict(merged.get(row['gate_code'], {}), **row,
                                           coordinate_source='WORKSPACE', layer_type='WORKSPACE_GIS_GATE')
        elif row['gate_code'] not in merged:
            missing_coordinates.append(row['gate_code'])
    database_count = None
    if bundle['storage_mode'] == 'postgres':
        rows = store.database_gates()['items']
        database_count = len(rows)
        for row in rows:
            if _point(row.get('geometry')):
                merged[row['gate_code']] = dict(merged.get(row['gate_code'], {}), **row,
                                               coordinate_source='POSTGRESQL', layer_type='DATABASE_GIS_GATE')
            elif row['gate_code'] not in merged:
                missing_coordinates.append(row['gate_code'])
    links = {}
    for feature in corridor['features']:
        props = feature['properties']
        if props.get('gate_code'):
            links.setdefault(props['gate_code'], []).append(props['id'])
    gates = [dict(row, coordinates=row['geometry']['coordinates'], canal_ids=links.get(code, []),
                  **_metadata()) for code, row in sorted(merged.items())]
    return gates, dict(database_gate_count=database_count,
                       excluded_gate_codes_without_coordinates=sorted(set(missing_coordinates)),
                       gate_count=len(gates), catalog_source=GATE_CATALOG.relative_to(ROOT).as_posix())


def simulation_corridor():
    corridor, _ = _read_corridor()
    bundle = load_bundle()
    gates, catalog = _catalog_gates(bundle, corridor)
    return dict(corridor=corridor, gates=gates, catalog=catalog,
                storage_mode=bundle['storage_mode'], **_metadata())


def simulation_timeline():
    items = list(monthly_inputs().values())
    return dict(items=items, total=len(items), start_month=items[0]['year_month'],
                end_month=items[-1]['year_month'], **_metadata())


def _month(year_month):
    if (not isinstance(year_month, str) or len(year_month) != 7 or year_month[4] != '-'
            or not year_month[:4].isdigit() or not year_month[5:].isdigit()
            or not 1 <= int(year_month[5:]) <= 12 or year_month[:4] == '0000'):
        raise WorkspaceError(422, 'year_month must be YYYY-MM with a valid calendar month.')
    result = monthly_inputs().get(year_month)
    if result is None:
        raise WorkspaceError(404, 'No simulation inputs for this month.')
    return result


def _anchors(month):
    upstream = month['tan_chau_ec_mS_m']
    downstream = month['my_tho_ec_mS_m']
    dry = int(month['year_month'][5:]) in {2, 3, 4, 5}
    # Explicit uncalibrated estuary scenario: amplify both local EC and the
    # downstream gradient in dry months. No simulated boundary is an observation.
    amplification = 6.0 if dry else 1.5
    estuary = downstream * amplification + max(0, downstream - upstream) * 0.4
    return [(0.0, upstream), (125.0, downstream), (175.0, estuary)], dry, amplification


def _idw(chainage, anchors):
    for x, value in anchors:
        if abs(x - chainage) < 1e-9:
            return value
    left, right = (anchors[:2] if chainage < 125 else anchors[1:])
    weights = [1 / abs(chainage - x) ** 2 for x, _ in (left, right)]
    return sum(weight * row[1] for weight, row in zip(weights, (left, right))) / sum(weights)


def _segments(month, axis, threshold):
    anchors, dry, _ = _anchors(month)
    result = []
    for index in range(35):
        start, end = index * 5.0, (index + 1) * 5.0
        ec = round(_idw((start + end) / 2, anchors), 6)
        intrusion = dry and ec >= threshold
        factor = (0.2 + 0.6 * min(ec / max(threshold, 1), 1) if intrusion else
                  1.5 - 0.8 * min(ec / max(threshold, 1), 1))
        result.append(dict(type='Feature', id=f'TIEN_SEG_{index + 1:02d}',
                           geometry=dict(type='LineString', coordinates=axis.section(start, end)),
                           properties=dict(segment_id=f'TIEN_SEG_{index + 1:02d}',
                               chainage_start_km=start, chainage_end_km=end,
                               chainage_km=(start + end) / 2, ec_mS_m=round(ec, 6),
                               start_ec_mS_m=round(_idw(start, anchors), 6),
                               end_ec_mS_m=round(_idw(end, anchors), 6),
                               salinity_g_l=ec_to_salinity_g_l(ec),
                               flow_direction='UPSTREAM_SALINE_INTRUSION' if intrusion else 'DOWNSTREAM_FRESHWATER',
                               flow_velocity_factor=round(max(0.2, min(1.5, factor)), 3),
                               flow_basis='ILLUSTRATIVE_SEASON_AND_EC_PROXY', **_metadata())))
    return result


def interpolate_river_profile(year_month: str, threshold_ec_ms_m: float = 150.0):
    threshold = _nonnegative(threshold_ec_ms_m, 'EC threshold')
    month = _month(year_month)
    _, coordinates = _read_corridor()
    return _segments(month, RiverAxis(coordinates), threshold)


def _isohalines(anchors, axis):
    boundaries = []
    for salinity in (1.0, 4.0):
        threshold = salinity / 0.0064
        roots = []
        for (a, ea), (b, eb) in zip(anchors, anchors[1:]):
            if ea == threshold:
                roots.append(a)
            if (ea - threshold) * (eb - threshold) < 0:
                low, high = a, b
                for _ in range(45):
                    middle = (low + high) / 2
                    if (_idw(middle, anchors) - threshold) * (ea - threshold) > 0:
                        low = middle
                    else:
                        high = middle
                roots.append((low + high) / 2)
            if eb == threshold:
                roots.append(b)
        crossings = [dict(chainage_km=round(x, 6), coordinate=axis.coordinate(x)) for x in sorted(set(roots))]
        if anchors[-1][1] < threshold:
            status, front = 'NOT_REACHED_AT_ESTUARY', None
        elif roots:
            status, front = 'WITHIN_CORRIDOR', max(roots)
        else:
            status, front = 'ENTIRE_CORRIDOR_ABOVE_THRESHOLD', 0.0
        boundaries.append(dict(salinity_g_l=salinity, threshold_ec_mS_m=threshold, status=status,
                               coordinate=axis.coordinate(front) if front is not None else None,
                               chainage_km=round(front, 6) if front is not None else None,
                               intrusion_distance_km=round(175 - front, 6) if front is not None else 0.0,
                               crossings=crossings, **_metadata()))
    return boundaries


def simulation_frame(year_month, open_below_ec=120.0, close_above_ec=150.0):
    try:
        gate_state(0, open_below_ec, close_above_ec)
    except (ValueError, TypeError, OverflowError) as exc:
        raise WorkspaceError(422, str(exc)) from exc
    month = _month(year_month)
    corridor, coordinates = _read_corridor()
    axis = RiverAxis(coordinates)
    anchors, dry, amplification = _anchors(month)
    bundle = load_bundle()
    catalog_gates, catalog = _catalog_gates(bundle, corridor)
    gates = []
    colors = dict(OPEN_INTAKE='green', CAUTION_TRANSITION='amber', CLOSED_SALINITY_BARRIER='red')
    for gate in catalog_gates:
        projection = axis.project(gate['coordinates'])
        ec = _idw(projection['chainage_km'], anchors)
        # The exposed EC and state use the same precision at threshold boundaries.
        ec = round(ec, 6)
        state = gate_state(ec, open_below_ec, close_above_ec)
        advisory_code, advisory_color, advisory_label = GATE_ADVISORIES[state]
        gates.append(dict(gate, **projection, simulated_outside_ec_mS_m=ec,
                          simulated_outside_salinity_g_l=ec_to_salinity_g_l(ec),
                          simulated_gate_state=state, state_color=colors[state],
                          advisory_code=advisory_code, advisory_color=advisory_color,
                          advisory_label=advisory_label, human_in_the_loop_Required=True,
                          canal_particle_intake_enabled=False))
    return dict(year_month=year_month, inputs=month, river_segments=_segments(month, axis, close_above_ec),
                gates=gates, catalog=catalog, isohaline_boundaries=_isohalines(anchors, axis),
                wind=month['wind'], thresholds=dict(open_below_ec_ms_m=open_below_ec,
                    close_at_or_above_ec_ms_m=close_above_ec),
                boundary_conditions=[dict(chainage_km=x, coordinate=axis.coordinate(x), ec_mS_m=round(ec, 6),
                    salinity_g_l=ec_to_salinity_g_l(ec),
                    basis='SIMULATED_ESTUARY_BOUNDARY' if x == 175 else 'MONTHLY_STATION_INPUT') for x, ec in anchors],
                assumptions=dict(idw_power=2, interpolation_neighbors='TWO_BRACKETING_AXIS_ANCHORS',
                    chainage_anchors_km=[0, 125, 175], segment_count=35, dry_season=dry,
                    estuary_amplification=amplification,
                    estuary_formula='my_tho_ec * amplification + max(0, my_tho_ec - tan_chau_ec) * 0.4',
                    estuary_calibration_status='UNCALIBRATED_SCENARIO',
                    geometry_status='REPRESENTATIVE_SCHEMATIC', flow_is_measured=False,
                    salinity_conversion_basis='EMPIRICAL_ESTIMATE_UNKNOWN_EC_TEMPERATURE_BASIS'),
                **_metadata())
