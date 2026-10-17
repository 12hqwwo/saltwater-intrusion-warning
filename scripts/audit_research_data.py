"""Recompute local evidence; never modify raw values or promote quality flags."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_research_workspace import compile_data, write_json

UNITS = {'water_level_m':'m', 'water_level_err_m':'m', 'tide_max_m':'m',
         'discharge_m3s':'m3/s', 'salinity_g_per_l':'g/L', 'precipitation_sum':'mm',
         'temperature_2m_max':'degC', 'temperature_2m_min':'degC', 'temperature_2m_mean':'degC',
         'et0_fao_evapotranspiration':'mm', 'windspeed_10m_max':'UNCONFIRMED',
         'relative_humidity_2m_mean':'%', 'shortwave_radiation_sum':'UNCONFIRMED'}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def summarize(frame, date_column, value_column):
    times = pd.to_datetime(frame[date_column], errors='coerce', utc=True)
    values = pd.to_numeric(frame[value_column], errors='coerce')
    valid = values.where(np.isfinite(values))
    ordered = times.dropna().drop_duplicates().sort_values()
    gaps = ordered.diff().dt.total_seconds().dropna()/86400
    q1, q3 = valid.quantile([.25,.75])
    # Only a review flag; extremes are not removed from observations or training.
    outliers = (valid < q1-3*(q3-q1)) | (valid > q3+3*(q3-q1))
    flags = next((c for c in ['quality_flag','source_quality','Approval Level'] if c in frame),None)
    date_only = frame[date_column].astype(str).str.fullmatch(r'\d{4}-\d{2}-\d{2}').all()
    first = str(ordered.min().date()) if date_only and len(ordered) else str(ordered.min()) if len(ordered) else None
    last = str(ordered.max().date()) if date_only and len(ordered) else str(ordered.max()) if len(ordered) else None
    return dict(rows=len(frame), finite_values=int(valid.notna().sum()), missing_or_nonfinite=int(valid.isna().sum()),
        invalid_dates=int(times.isna().sum()), first=first, last=last, time_precision='DATE_ONLY' if date_only else 'SOURCE_TIMESTAMP',
        duplicate_times=int(times.duplicated(keep=False).sum()),
        duplicate_rows=int(frame.duplicated().sum()), median_gap_days=float(gaps.median()) if len(gaps) else None,
        max_gap_days=float(gaps.max()) if len(gaps) else None,
        gaps_over_twice_median=int((gaps>2*gaps.median()).sum()),
        gap_days_histogram={str(k):int(v) for k,v in gaps.value_counts().sort_index().items()},
        min=float(valid.min()) if valid.notna().any() else None,max=float(valid.max()) if valid.notna().any() else None,
        negative_values=int((valid<0).sum()), extreme_3IQR_review_only=int(outliers.sum()),
        quality_counts=frame[flags].fillna('MISSING').value_counts().to_dict() if flags else {'UNSPECIFIED':len(frame)},
        exclusions='NONE by audit; negative water level may be legitimate; IQR is not a validity rule')

def main():
    out=ROOT/'data/research/audit';out.mkdir(parents=True,exist_ok=True)
    sites, observations, sources, gates=compile_data()
    ec=pd.DataFrame(observations)
    report=dict(generated_at=datetime.now(timezone.utc).isoformat(),database_checked=False,series=[],
                sources=sources,station_metadata=sites,gate_catalog=gates,
                classifications={'MRC':'OBSERVATION; original quality retained','RIA2':'OBSERVATION; inherited transcription',
                    'DAHITI':'SATELLITE_DERIVED_WATER_LEVEL; not a gate level',
                    'GloFAS':'MODEL_REANALYSIS_DISCHARGE', 'OpenMeteo':'ARCHIVE_MODEL_PRODUCT; explicit ERA5 only where requested',
                    'GFZ_SONDOC':'HISTORICAL_SALINITY_OBSERVATION', 'GFZ_TANCHAU':'RECONSTRUCTED_GAP_FILLED_DISCHARGE',
                    'SIWRR':'AGENCY_FORECAST; excluded from observed labels', 'synthetic':'SIMULATION; excluded'},
                raw_file_inventory=[],overlap=[],mrc_recheck=[])
    for site in sites:
        f=ec[ec.site_code.eq(site['site_code'])]
        report['series'].append(dict(source=site['provider'],station=site['site_code'],parameter='EC',unit='mS/m',
            **summarize(f,'observed_date','ec_mS_m')))
    fresh=ROOT/'data/external/mrc_20261014_network'
    for p in fresh.glob('*.csv'):
        if 'pairs' in p.name or 'quarantine' in p.name:continue
        f=pd.read_csv(p)
        report['series'].append(dict(file=p.relative_to(ROOT).as_posix(),sha256=digest(p),source='MRC_LATEST_RETRIEVAL',
            station=f.site_code.iloc[0],parameter=f.parameter.iloc[0],unit=f.unit.iloc[0],**summarize(f,'observed_at','value')))
        if f.parameter.iloc[0]=='Conductivity':
            old=ec[ec.site_code.eq(f.site_code.iloc[0])]
            merged=old.merge(f,on='observed_at',how='outer',indicator=True)
            report['mrc_recheck'].append(dict(station=f.site_code.iloc[0],rows=len(merged),
                unmatched=int(merged['_merge'].ne('both').sum()),
                changed_values=int((merged.ec_mS_m-merged.value).abs().gt(1e-9).sum())))
    paths=list((ROOT/'data/raw/dahiti').glob('*.csv'))+list((ROOT/'data/raw/meteorology/openmeteo').glob('*.csv'))
    paths+=list((ROOT/'data/raw/tide/uhslc').glob('*.csv'))
    paths += [ROOT/'data/external/research_tls_20261010_215230'/n for n in ['sondoc_observations.csv','tanchau_discharge_monthly.csv']]
    for p in paths:
        f=pd.read_csv(p);datecol=next(c for c in ['observed_at','date','month_start'] if c in f)
        sitecol=next((c for c in ['site_code','station'] if c in f),None)
        groups=f.groupby(sitecol) if sitecol else [(p.stem,f)]
        for station,group in groups:
            for column in UNITS:
                if column not in group:continue
                row=dict(file=p.relative_to(ROOT).as_posix(),sha256=digest(p),station=str(station),parameter=column,
                         unit=UNITS[column],**summarize(group,datecol,column))
                coords={c:group[c].dropna().drop_duplicates().tolist() for c in ['lat','lon','target_lat','target_lon'] if c in group}
                row.update(source_coordinates=coords,crs='NOT_CONFIRMED_BY_THIS_AUDIT')
                report['series'].append(row)
                # Calendar intersection is necessary, not proof of availability at issue.
                alias={'TanChau':'MRC_VN_019803','TANCHAU':'MRC_VN_019803','MyTho':'MRC_VN_019805','MYTHO':'MRC_VN_019805'}
                if station in alias:
                    labels=set(ec.loc[ec.site_code.eq(alias[station]),'observed_date'].str[:7])
                    months=set(group.loc[pd.to_numeric(group[column],errors='coerce').notna(),datecol].astype(str).str[:7])
                    report['overlap'].append(dict(file=row['file'],station=station,parameter=column,
                        months_with_input=len(months),months_with_observed_ec=len(labels),intersection_months=len(months&labels),
                        input_months_without_ec=len(months-labels),training_labels_created=0,
                        available_at_forecast_origin='NOT_CONFIRMED; not used by monthly EC-only backtest'))
    for p in (ROOT/'data/raw').rglob('*'):
        if p.is_file():report['raw_file_inventory'].append(dict(file=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=digest(p),
            detailed_numeric_audit='CSV series above, otherwise NOT_RUN (including NetCDF and GIS)'))
    report['source_integrity_note']='Original RIA2 hashes checked separately from transcription correctness; neither implies VALIDATED.'
    write_json(out/'audit.json',report)
    flat=[{k:v for k,v in r.items() if not isinstance(v,(dict,list))} for r in report['series']]
    pd.DataFrame(flat).to_csv(out/'series.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(report['overlap']).to_csv(out/'input_label_overlap.csv',index=False)
    print(json.dumps(dict(series=len(flat),raw_files=len(report['raw_file_inventory']),mrc_recheck=report['mrc_recheck'])))

if __name__=='__main__':main()
