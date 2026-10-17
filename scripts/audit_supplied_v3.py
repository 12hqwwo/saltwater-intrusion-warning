"""Read-only audit of supplied v3 workbook, CSV and spatial catalogue.

Run with Python containing openpyxl and pandas. No import to production data.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import openpyxl
import pandas as pd


def audit(source, out):
    out.mkdir(parents=True, exist_ok=False)
    names = ['WebGIS_DongThap_TienGiang_Master_Dataset_v3.xlsx',
             'WebGIS_ML_Time_Series_Ready_v3.csv', 'webgis_dongthap_tiengiang_spatial_v3.json']
    manifest = []
    for name in names:
        origin = source / name
        shutil.copyfile(origin, out / name)
        manifest.append(dict(file=name, source_path=str(origin), sha256=hashlib.sha256(origin.read_bytes()).hexdigest(),
                             received_at=datetime.now(timezone.utc).isoformat(), status='USER_SUPPLIED_UNVERIFIED'))
    wb = openpyxl.load_workbook(out / names[0], read_only=True, data_only=True)
    sheets = {s.title: list(s.values) for s in wb}
    df = pd.read_csv(out / names[1])
    df['date'] = pd.to_datetime(df.obs_date, errors='raise')
    issues, stations = [], []
    def issue(row, reason, expected=None):
        issues.append(dict(sample_id=row.ml_sample_id, station=row.station_code, date=row.obs_date,
                           reason=reason, expected=expected))
    for code, group in df.groupby('station_code'):
        group = group.sort_values('date')
        lookup = {r.date:r for r in group.itertuples()}
        dates = sorted(set(group.date))
        gaps = [(b-a).days for a,b in zip(dates,dates[1:])]
        longest = run = 1
        for gap in gaps:
            run = run + 1 if gap == 1 else 1
            longest = max(longest, run)
        stations.append(dict(station=code, rows=len(group), unique_dates=len(dates), first=str(dates[0].date()),
                             last=str(dates[-1].date()), longest_daily_run=longest,
                             largest_gap_days=max(gaps, default=0), next1d_labels=int(group.target_salinity_next1d_g_l.notna().sum()),
                             full_hydromet_next1d=int(group[['target_salinity_next1d_g_l','feat_xuanhoa_tide_max_m','feat_xuanhoa_tide_min_m','feat_canal_water_level_m','feat_rainfall_24h_mm']].notna().all(axis=1).sum())))
        for row in group.itertuples():
            for offset, field in [(-1,'feat_salinity_lag1_g_l'),(-2,'feat_salinity_lag2_g_l'),(1,'target_salinity_next1d_g_l')]:
                value = getattr(row, field)
                neighbour = lookup.get(row.date + pd.Timedelta(days=offset))
                if pd.notna(value) and (neighbour is None or abs(value-neighbour.target_salinity_max_g_l)>1e-8):
                    issue(row, 'CALENDAR_MISMATCH_'+field, None if neighbour is None else neighbour.target_salinity_max_g_l)
            for threshold, field in [(.5,'target_exceed_0p5_gl'),(.7,'target_exceed_0p7_gl'),(1.,'target_exceed_1p0_gl'),(2.,'target_exceed_2p0_gl')]:
                if pd.notna(getattr(row,field)) and getattr(row,field) != int(row.target_salinity_max_g_l>threshold):
                    issue(row,'THRESHOLD_MISMATCH_'+field)
    spatial = json.loads((out / names[2]).read_text(encoding='utf-8-sig'))
    features = spatial['features']
    raw_river = sheets['03_Salinity_River_Series'][4:]
    raw_canal = sheets['04_Salinity_Canal_Interior'][4:]
    raw_lookup = {}
    for row in raw_river:
        if isinstance(row[7], (int,float)):
            raw_lookup.setdefault((row[1],str(row[4])), []).append(row[7])
    for row in raw_canal:
        if isinstance(row[6], (int,float)):
            raw_lookup.setdefault((row[1],str(row[4])), []).append(row[6])
    for row in df.itertuples():
        values = raw_lookup.get((row.station_code,row.obs_date),[])
        if not values or abs(max(values)-row.target_salinity_max_g_l)>1e-8:
            issue(row,'TARGET_REQUIRES_MEASUREMENT_LOCATION_DISAMBIGUATION', max(values) if values else None)
    wb_ml = pd.DataFrame(sheets['13_ML_Time_Series_Ready'][4:], columns=sheets['13_ML_Time_Series_Ready'][3])
    urls = set(df.source_url.dropna())
    for name,rows in sheets.items():
        for row in rows:
            for cell in row:
                if isinstance(cell,str) and cell.startswith(('http://','https://')):
                    urls.add(cell)
    summary = dict(files=manifest, sheet_rows={n:len(r)-4 for n,r in sheets.items()},
        csv_rows=len(df), workbook_ml_rows=len(wb_ml), station_count=df.station_code.nunique(),
        duplicate_station_dates=int(df.duplicated(['station_code','obs_date'],keep=False).sum()),
        next1d_label_count=int(df.target_salinity_next1d_g_l.notna().sum()),
        next1d_zero_labels=int(df.target_salinity_next1d_g_l.eq(0).sum()),
        full_hydromet_next1d=int(df[['target_salinity_next1d_g_l','feat_xuanhoa_tide_max_m','feat_xuanhoa_tide_min_m','feat_canal_water_level_m','feat_rainfall_24h_mm']].notna().all(axis=1).sum()),
        split_roles=df.ml_split_role.value_counts().to_dict(),
        issue_counts=dict(Counter(i['reason'] for i in issues)),
        spatial_features=len(features), spatial_classes=dict(Counter(f['properties'].get('feature_class') for f in features)),
        spatial_location_status=dict(Counter(f['properties'].get('location_status','MISSING') for f in features)),
        spatial_null_geometries=sum(f.get('geometry') is None for f in features),
        river_measurement_regimes=dict(Counter(r[6] for r in raw_river)),
        acceptance='STAGING_ONLY_NOT_APPROVED_FOR_TRAINING_OR_GATE_ADVICE',
        note='Counts are internal consistency checks, not independent verification of measurement values.')
    for name, payload in [('audit.json',summary),('station_coverage.json',stations),('row_issues.json',issues),('source_urls.json',sorted(urls))]:
        (out/name).write_text(json.dumps(payload,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,default=str))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    audit(a.source,a.out)
