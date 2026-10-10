# FES2022b source snapshot

This directory contains the FES2022 tide-elevation product, version `b`, used for
the Mekong-coast candidate screening. The NetCDF metadata identifies:

- product: FES2022 tide elevations, extrapolated grids;
- version: `b`;
- DOI: `10.24400/527896/a01-2024.004`;
- owner/credits: CNES; LEGOS, NOVELTIS and CLS;
- amplitude unit: centimetres;
- phase unit: degrees;
- licence: <https://www.aviso.altimetry.fr/en/data/data-access/fileadmin/documents/data/License_Aviso.pdf>.

The `ocean_tide_extrapolated/` folder retains both the downloaded `.nc.xz`
archives and their decompressed `.nc` working copies. The archives were saved
locally from 8 to 9 October 2026 (UTC+07); extraction completed on 10 October
2026. Exact timestamps, sizes and SHA-256 hashes are recorded in
`source_manifest.json`. The decompressed files were verified against the
archives before this manifest was written.

Current scientific status:

- M2, S2, K1 and O1 plus the FES2022b mask are present;
- three offshore candidates pass the local finite-value/native-mask file check;
- all candidates remain `REVIEW`;
- coastline representation, vertical datum and hydrological representativeness
  are not yet approved;
- final outputs `04_tide_points.geojson`, `05_tide_hourly.csv` and
  `06_tide_monthly.csv` have not been produced.

Do not substitute the UHSLC Vung Tau daily series for FES2022b predictions.
