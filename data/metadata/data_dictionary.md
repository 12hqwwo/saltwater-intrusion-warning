# Data Dictionary -- Mo hinh du bao xam nhap man DBSCL
*Tao: 2026-09-02 01:57*

## Tram quan trac
| Ten tram | Lat | Lon | Ma MRC | Song |
|---|---|---|---|---|
| TanChau | 10.804 | 105.234 | 019803 | Mekong (song Tien, thuong) |
| MyTho   | 10.360 | 106.360 | 019805 | Song Tien (cua song) |

## Bien du lieu
| Bien | Don vi | Tan suat goc | Tan suat processed | Nguon | Ngay tai | Pham vi |
|---|---|---|---|---|---|---|
| conductivity_mS_per_m | mS/m | Thang | Thang | MRC Data Portal | 2026-08-31 | 1985-05 -> 2023-12 |
| precip_mm | mm | Ngay | Thang (tong) | Open-Meteo ERA5-Land | 2026-09-02 | 1985-01 -> 2026-08 |
| temp_max/min/mean_c | C | Ngay | Thang (TB) | Open-Meteo ERA5-Land | 2026-09-02 | 1985-01 -> 2026-08 |
| et0_mm | mm | Ngay | Thang (tong) | Open-Meteo FAO PM | 2026-09-02 | 1985-01 -> 2026-08 |
| wind_max_ms | m/s | Ngay | Thang (TB) | Open-Meteo | 2026-09-02 | 1985-01 -> 2026-08 |
| rh_pct | % | Ngay | Thang (TB) | Open-Meteo | 2026-09-02 | 1985-01 -> 2026-08 |
| radiation_mj | MJ/m2 | Ngay | Thang (tong) | Open-Meteo | 2026-09-02 | 1985-01 -> 2026-08 |
| water_level_m | m | -- | -- | DAHITI altimetry | MISSING (xem PLACEHOLDER) | -- |


## Ghi chu ky thuat
- Temporal alignment: conductivity la thang -> meteo downsample ve thang
- Oulier conductivity: gia tri > 80 mS/m co the la loi cam bien (kiem tra 1998)
- Open-Meteo nguon: ERA5-Land reanalysis (5 km resolution)
- Timezone: UTC+07:00

## Tham khao
- MRC: https://portal.mrcmekong.org/time-series
- Open-Meteo: https://open-meteo.com/en/docs/historical-weather-api
- DAHITI: https://dahiti.dgfi.tum.de/
- SIWRR: https://www.siwrr.org.vn/
