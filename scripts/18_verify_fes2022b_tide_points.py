#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Validate three candidate FES2022b tide points against *local* four-constituent NetCDF and native mask.

Run from D:\Study\TLCN:
    .\.venv-api\Scripts\python.exe .\scripts\18_verify_fes2022b_tide_points.py

This never marks a point VERIFIED. Coastline and datum need independent checks.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'data' / 'raw' / 'tide' / 'fes2022b' / 'ocean_tide_extrapolated'
CURATED = ROOT / 'data' / 'processed' / 'tide'
INPUT = CURATED / '04_tide_points_candidates.geojson'
OUTPUT = CURATED / '04_tide_points_checked.geojson'
CSV_OUT = CURATED / '04_tide_points_validation.csv'
CONS = ('m2', 's2', 'k1', 'o1')
MASK_FILE = BASE / 'mask_fes2022B.nc'


def nearest_indices(ds: xr.Dataset, lat: float, lon: float):
    y = np.asarray(ds['lat'].values)
    x = np.asarray(ds['lon'].values)
    yi = int(np.argmin(np.abs(y-lat)))
    xi = int(np.argmin(np.abs(x-lon)))
    if abs(y[yi]-lat)>0.001 or abs(x[xi]-lon)>0.001:
        raise ValueError('Point is not on the requested FES grid')
    return yi, xi


def scalar_at(ds, var, lat, lon):
    yi,xi=nearest_indices(ds,lat,lon)
    return float(ds[var].isel(lat=yi,lon=xi).values)


def check():
    if not INPUT.exists():
        raise SystemExit('Missing GeoJSON: '+str(INPUT))
    for fn in [MASK_FILE] + [BASE/(c+'_fes2022.nc') for c in CONS]:
        if not fn.exists():
            raise SystemExit('Missing source file: '+str(fn))
    data=json.loads(INPUT.read_text(encoding='utf-8-sig'))
    fs=data.get('features') or []
    if len(fs)!=3:
        raise SystemExit('Expected exactly 3 candidates, got '+str(len(fs)))
    ds_mask=xr.open_dataset(MASK_FILE)
    dsets={c:xr.open_dataset(BASE/(c+'_fes2022.nc')) for c in CONS}
    report=[]
    try:
        for feat in fs:
            prop=feat['properties']; code=prop['point_code']
            lon,lat=feat['geometry']['coordinates']
            yi,xi=nearest_indices(ds_mask,lat,lon)
            mask=int(ds_mask['mask'].isel(lat=yi,lon=xi).values)
            values=np.asarray(ds_mask['mask'].isel(lat=slice(yi-1,yi+2),lon=slice(xi-1,xi+2)).values)
            native3=bool(values.shape==(3,3) and np.all(np.isfinite(values)) and np.all(values==0))
            samples={}
            bad=[]
            expected_m2_amplitude=float(prop['m2_amplitude_cm'])
            expected_m2_phase=float(prop['m2_phase_deg'])
            for c,ds in dsets.items():
                amp=scalar_at(ds,'amplitude',lat,lon)
                phase=scalar_at(ds,'phase',lat,lon)
                if not (math.isfinite(amp) and math.isfinite(phase)):
                    bad.append(c+' non-finite')
                if ds['amplitude'].attrs.get('units') != 'cm':
                    bad.append(c+' amplitude units not cm')
                if ds['phase'].attrs.get('units') != 'degrees':
                    bad.append(c+' phase units not degrees')
                samples[c]=(amp,phase)
                prop[c+'_amplitude_cm']=amp
                prop[c+'_phase_deg']=phase
            if mask!=0:
                bad.append('mask_code != 0')
            if not native3:
                bad.append('native3x3 != true')
            if abs(samples['m2'][0]-expected_m2_amplitude)>0.05 or abs(samples['m2'][1]-expected_m2_phase)>0.05:
                bad.append('M2 does not match supplied QGIS screenshot')
            # Do not overwrite status REVIEW or claim coastline was validated.
            prop['fes_four_constituents_check'] = 'PASS_FILE_SAMPLE' if not bad else 'FAIL_FILE_SAMPLE'
            prop['validation_status'] = 'REVIEW'
            prop['mask_code']=mask
            prop['native_3x3']=native3
            prop['file_check_note']='; '.join(bad) if bad else 'All M2/S2/K1/O1 finite, native 3x3; coastline and datum still unchecked'
            report.append({'point_code':code, 'latitude':lat,'longitude':lon,
                           'mask_code':mask,'native_3x3':native3,
                           'm2_cm':samples['m2'][0],'s2_cm':samples['s2'][0],
                           'k1_cm':samples['k1'][0],'o1_cm':samples['o1'][0],
                           'file_check':prop['fes_four_constituents_check'],
                           'note':prop['file_check_note']})
            print(code, '=>', prop['fes_four_constituents_check'], '(still REVIEW)')
    finally:
        ds_mask.close()
        for ds in dsets.values(): ds.close()
    OUTPUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with CSV_OUT.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f, fieldnames=list(report[0].keys()));w.writeheader();w.writerows(report)
    print('Saved:',OUTPUT)
    print('Saved:',CSV_OUT)
    print('IMPORTANT: This is not independent shoreline/bathymetry verification.')

if __name__=='__main__':
    check()
