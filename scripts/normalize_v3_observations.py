"""Normalize supplied salinity rows into a review-only ledger; never infer labels.

Requires openpyxl. No geocoding, interpolation, time-zone assignment or DB write.
"""
from collections import Counter
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import argparse
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'data/external/user_v3_review_20261015'


def normalize(workbook, workbook_sha):
    records, rejected = [], []
    def add(sheet, row_number, row, position, value, date_value, time_value, regime, url, name):
        reasons = []
        try:
            date.fromisoformat(str(date_value))
        except (TypeError, ValueError):
            reasons.append('INVALID_OR_INTERVAL_DATE')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            reasons.append('MISSING_OR_INVALID_SALINITY')
        if not isinstance(url,str) or not url.startswith(('https://','http://')):
            reasons.append('MISSING_SOURCE_URL')
        if reasons:
            rejected.append(dict(sheet=sheet, row=row_number, position=position, reasons=reasons))
            return
        # A provisional key partitions physical measurement contexts. It does
        # not certify station identity or relationship with any gate.
        point_key = f'{row[1]}::{position}'
        records.append(dict(record_id=f'{sheet}:{row_number}:{position}', original_id=row[0],
            source_station_code=row[1], source_station_name=name, measurement_point_key=point_key,
            position=position, observed_date=str(date_value), source_time_or_period=time_value,
            measurement_regime=regime, parameter='SALINITY', value=value, unit='g/L',
            source_url=url, workbook_sha256=workbook_sha, source_locator=f'{sheet}!row {row_number}',
            quality_flag='UNVERIFIED', source_verified=False, training_eligible=False,
            gate_decision_eligible=False, observed_at=None, window_start=None, window_end=None,
            geometry=None, availability_at=None,
            review_reasons=['ORIGINAL_TABLE_NOT_VERIFIED','MEASUREMENT_WINDOW_NOT_VERIFIED'] +
                (['HISTORICAL_COMPARISON_DERIVATION'] if str(regime).startswith('HIST_MATCHED') else []) +
                (['SEASONAL_PEAK_NOT_DAILY_LABEL'] if regime=='SEASONAL_PEAK_OBS' else [])))
    sheet = '03_Salinity_River_Series'
    for index,row in enumerate(list(workbook[sheet].values)[4:],start=5):
        add(sheet,index,row,'RIVER_REPORTED',row[7],row[4],row[5],row[6],row[10],row[2])
    sheet = '04_Salinity_Canal_Interior'
    for index,row in enumerate(list(workbook[sheet].values)[4:],start=5):
        for position,column in [('INTERIOR_0M',6),('INTERIOR_200M',7)]:
            add(sheet,index,row,position,row[column],row[4],row[5],'FIXED_TIME_REPORTED',row[12],row[2])
    keys = Counter((r['measurement_point_key'],r['observed_date'],r['source_time_or_period'],r['measurement_regime']) for r in records)
    for r in records:
        key = (r['measurement_point_key'],r['observed_date'],r['source_time_or_period'],r['measurement_regime'])
        if keys[key]>1:
            r['review_reasons'].append('DUPLICATE_CONTEXT_REQUIRES_REVIEW')
    return dict(schema_version=1,status='REVIEW_ONLY',records=records,rejected=rejected,
                counts=dict(records=len(records), rejected=len(rejected),
                            measurement_points=len({r['measurement_point_key'] for r in records}),
                            positions=dict(Counter(r['position'] for r in records)),
                            training_eligible=0, gate_decision_eligible=0))


def main(folder):
    audit = json.loads((folder/'audit.json').read_text(encoding='utf-8'))
    source = next(r for r in audit['files'] if r['file'].endswith('.xlsx'))
    path = folder/source['file']
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if sha != source['sha256']:
        raise ValueError('Original checksum mismatch')
    workbook = openpyxl.load_workbook(path,read_only=True,data_only=True)
    data = normalize(workbook,sha)
    workbook.close()
    output = folder/'normalized_review.json'
    raw = (json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
    output.write_bytes(raw)
    output.with_suffix('.manifest.json').write_text(json.dumps(dict(file=output.name,sha256=hashlib.sha256(raw).hexdigest(),
        source_sha256=sha,method='normalize_v3_observations.py; source rows unchanged; contexts partitioned; no aggregation',
        counts=data['counts']),indent=2),encoding='utf-8')
    print(json.dumps(data['counts']))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',type=Path,default=DEFAULT)
    main(parser.parse_args().folder)
