"""Refresh canonical public sources and optionally download selected ERA5 weather.

Canonical Son Doc/Tan Chau files live under ``data/external/sources``. Each
execution writes only run-specific provenance and weather files under
``data/external/download_runs`` (or ``data/external/``); it never imports into PostgreSQL.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import ssl
from urllib.error import URLError
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GFZ = "https://datapub.gfz-potsdam.de/download/10.5880.GFZ.4.4.2024.004-QWn/"
FILES = {
    "sondoc_source.csv": ("2024-004_Apel_salinity_SONDOC_1996-2016.csv", "c79c658321c73f2ff0e24a154fa09eca1fe9ce6d1119cc00a29d6777eb2332e2"),
    "tanchau_discharge_source.csv": ("2024-004_Apel-et-al_discharge_Qmonthly_TanChau_1964-2017_gaps-filled.csv", "d6479cb03b7d5dc4fc3df24cbc67adabdba8606c608cc1688441b76852be0a3f"),
    "gfz_description.pdf": ("2024-004_Apel-et-al_data-description.pdf", "00c4373f3df5ddb2a92cee4003bcd95acee6a97ffe6e1011cacfcc95a7cf995d"),
}
SOURCE_LOCATIONS = {
    "sondoc_source.csv": ("sondoc", "sondoc_source.csv"),
    "tanchau_discharge_source.csv": ("tanchau_discharge", "tanchau_discharge_source.csv"),
    "gfz_description.pdf": ("sondoc", "gfz_description.pdf"),
}
SITES = {"MYTHO": (10.35912163, 106.3529997), "TANCHAU": (10.80062008, 105.2480164)}
WEATHER = {"precipitation_sum": ("precipitation_sum", "mm", "sum"),
           "temperature_2m_mean": ("temperature_mean", "°C", "mean"),
           "et0_fao_evapotranspiration": ("evapotranspiration_sum", "mm", "sum")}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def project_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_tls_context():
    # Enforce certificate verification, safe TLS protocol, host check, and strict cipher defaults.
    try:
        import truststore
        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:
        context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
    extra_ca = os.getenv("WEBGIS_CA_BUNDLE")
    if extra_ca and Path(extra_ca).is_file():
        context.load_verify_locations(cafile=extra_ca)
    else:
        try:
            import certifi
            context.load_verify_locations(cafile=certifi.where())
        except Exception:
            pass
    if extra_ca and Path(extra_ca).is_file():
        context.load_verify_locations(cafile=extra_ca)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.set_alpn_protocols(["http/1.1"])
    return context


def download(url, path, expected=None):
    # No credentials, executable content, or third-party serialized models.
    context = create_tls_context()
    parts = urlsplit(url)
    url = urlunsplit((parts.scheme, parts.netloc, quote(parts.path, safe='/%:@'), parts.query, parts.fragment))
    try:
        with urlopen(Request(url, headers={"User-Agent": "WebGIS-academic-data-review/1.0"}),
                     timeout=55, context=context) as response:
            blob = response.read(20_000_001)
            final_url = response.url
    except URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            raise RuntimeError(
                f"HTTPS certificate verification failed for {url}. "
                "Native truststore and certifi are enabled; certificate checking remains on. "
                "Check the Windows trust store, the server certificate chain, or an "
                "organisation-managed HTTPS proxy. If your administrator provides an "
                "approved PEM CA bundle, set WEBGIS_CA_BUNDLE to that file. "
                "Retry with --out pointing to a new directory."
            ) from exc
        raise
    if len(blob) > 20_000_000:
        raise ValueError("Response exceeds the 20 MB limit.")
    digest = hashlib.sha256(blob).hexdigest()
    if expected and digest != expected:
        raise ValueError("Source changed; inspect its new version before updating the pinned checksum.")
    path.write_bytes(blob)
    return {"url": url, "final_url": final_url, "file": path.name, "bytes": len(blob), "sha256": digest,
            "fetched_at": datetime.now(timezone.utc).isoformat()}


def normalize_sondoc(path):
    raw = pd.read_csv(path, sep=";", comment="#", encoding="utf-8-sig", dtype=str)
    if list(raw.columns) != ["DATETIME", "SALINITY [g/l]"]:
        raise ValueError("Unexpected Son Doc header.")
    when = pd.to_datetime(raw.DATETIME, format="%Y-%m-%d %H:%M:%S", errors="coerce")
    salinity = pd.to_numeric(raw["SALINITY [g/l]"], errors="coerce")
    bad = when.isna() | salinity.isna() | (salinity < 0) | (salinity > 70)
    clean = pd.DataFrame({"observed_at": when[~bad].dt.strftime("%Y-%m-%d %H:%M:%S+07:00"),
                          "salinity_g_l": salinity[~bad].round(3),
                          "raw_timestamp": raw.DATETIME[~bad],
                          "source_quality": "VERIFIED_STRUCTURE_ORIGINAL_SERIES_UNCERTIFIED"})
    quarantine = raw[bad].copy()
    qa = {"rows_read": len(raw), "rows_clean": len(clean), "rows_quarantined": int(bad.sum()),
          "first_clean": clean.observed_at.min() if not clean.empty else None,
          "last_clean": clean.observed_at.max() if not clean.empty else None,
          "salinity_min_g_l": float(clean.salinity_g_l.min()) if not clean.empty else None,
          "salinity_max_g_l": float(clean.salinity_g_l.max()) if not clean.empty else None}
    return clean, quarantine, qa


def normalize_discharge(path):
    raw = pd.read_csv(path, sep=";", comment="#", encoding="utf-8-sig", dtype=str)
    if list(raw.columns) != ["DATE", "Q_monthly [m3/s]"]:
        raise ValueError("Unexpected Tan Chau discharge header.")
    when = pd.to_datetime(raw.DATE, format="%Y-%m-%d", errors="coerce")
    q = pd.to_numeric(raw["Q_monthly [m3/s]"], errors="coerce")
    bad = when.isna() | q.isna() | (q < 0)
    clean = pd.DataFrame({"month_start": when[~bad].dt.strftime("%Y-%m-%d"),
                          "discharge_m3_s": q[~bad].round(1),
                          "source_quality": "GFZ_GAP_FILLED_RESEARCH_SERIES"})
    qa = {"rows_read": len(raw), "rows_clean": len(clean), "rows_quarantined": int(bad.sum()),
          "first_month": clean.month_start.min(), "last_month": clean.month_start.max()}
    return clean, qa


def weather_tables(payload, station, expected_start, expected_end):
    daily = payload["daily"]
    frame = pd.DataFrame({"time": daily["time"],
                          "precipitation_sum": daily["precipitation_sum"],
                          "temperature_mean": daily["temperature_2m_mean"],
                          "evapotranspiration_sum": daily["et0_fao_evapotranspiration"]})
    frame["station"] = station
    frame["date"] = pd.to_datetime(frame["time"])
    full_index = pd.date_range(expected_start, expected_end, freq="D")
    if len(frame) != len(full_index) or (frame["date"].values != full_index.values).any():
        raise ValueError("Weather date sequence is not daily continuous or does not match request range.")
    frame["month_start"] = frame["date"].dt.to_period("M").dt.to_timestamp().dt.strftime("%Y-%m-%d")
    grouped = frame.groupby(["station", "month_start"], as_index=False).agg({
        "precipitation_sum": "sum",
        "temperature_mean": "mean",
        "evapotranspiration_sum": "sum"
    })
    for col in ["precipitation_sum", "temperature_mean", "evapotranspiration_sum"]:
        grouped[col] = grouped[col].round(4)
    daily_export = frame[["station", "time", "precipitation_sum", "temperature_mean", "evapotranspiration_sum"]].copy()
    daily_export.rename(columns={"time": "date"}, inplace=True)
    return daily_export, grouped


def combine_targets(weather_monthly, master_df):
    merged = weather_monthly.merge(master_df, on=["station", "month_start"], how="left")
    missing_targets = merged["conductivity_mS_per_m"].isna()
    if missing_targets.any():
        print(f"Warning: {missing_targets.sum()} rows lack target EC in master.")
    return merged


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    default_out = ROOT / "data/external/download_runs/research_step07" if (ROOT / "data/external/download_runs").is_dir() else ROOT / "data/external/research_step07"
    parser.add_argument("--out", type=Path, default=default_out)
    parser.add_argument("--sources", type=Path, default=ROOT / "data/external/sources")
    parser.add_argument("--weather-start", default="1985-01-01")
    parser.add_argument("--weather-end", help="Optional completed date, e.g. 2026-09-30. Adds both stations' ERA5.")
    default_master = ROOT / "data/processed/master_timeseries.csv" if (ROOT / "data/processed/master_timeseries.csv").exists() else ROOT / "data/archive/legacy_analysis/master_timeseries.csv"
    parser.add_argument("--master", type=Path, default=default_master)
    args = parser.parse_args()
    try:
        args.out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error(f"Output directory already exists: {args.out}. "
                     "Keep it for inspection and choose a new --out directory.")
    manifest = {"schema_version": 1, "retrievals": [], "errors": [], "gate_decision_eligible": False}
    try:
        if args.sources.is_dir():
            source_paths = {
                local: args.sources / folder / filename
                for local, (folder, filename) in SOURCE_LOCATIONS.items()
            }
            for path in source_paths.values():
                path.parent.mkdir(parents=True, exist_ok=True)
            for local, (remote, checksum) in FILES.items():
                source_path = source_paths[local]
                if source_path.exists():
                    digest = file_sha256(source_path)
                    if digest != checksum:
                        raise ValueError(
                            f"Canonical source checksum mismatch: {source_path}. "
                            "Inspect it before refreshing or replacing the file."
                        )
                    record = {
                        "url": GFZ + remote,
                        "final_url": GFZ + remote,
                        "file": source_path.name,
                        "bytes": source_path.stat().st_size,
                        "sha256": digest,
                        "checked_at": datetime.now(timezone.utc).isoformat(),
                        "retrieval_mode": "REUSED_PINNED_CANONICAL_SOURCE",
                    }
                else:
                    record = download(GFZ + remote, source_path, checksum)
                    record["retrieval_mode"] = "DOWNLOADED_CANONICAL_SOURCE"
                record["canonical_path"] = project_path(source_path)
                record.update(license="CC-BY-4.0", citation="Apel, H.; Khiem, M.; Nguyen, H.Q.; Toan, T.Q. (2024), doi:10.5880/GFZ.4.4.2024.004")
                manifest["retrievals"].append(record)
            son_output = args.sources / "sondoc/sondoc_observations.csv"
            quarantine_output = args.sources / "sondoc/sondoc_quarantine.csv"
            discharge_output = args.sources / "tanchau_discharge/tanchau_discharge_monthly.csv"
            son, rejected, sonqa = normalize_sondoc(source_paths["sondoc_source.csv"])
            son.to_csv(son_output, index=False)
            rejected.to_csv(quarantine_output, index=False)
            discharge, qqa = normalize_discharge(source_paths["tanchau_discharge_source.csv"])
            discharge.to_csv(discharge_output, index=False)
            manifest["canonical_outputs"] = {
                "sondoc_observations": project_path(son_output),
                "sondoc_quarantine": project_path(quarantine_output),
                "tanchau_discharge_monthly": project_path(discharge_output),
            }
        else:
            for local, (remote, checksum) in FILES.items():
                record = download(GFZ + remote, args.out / local, checksum)
                record.update(license="CC-BY-4.0", citation="Apel, H.; Khiem, M.; Nguyen, H.Q.; Toan, T.Q. (2024), doi:10.5880/GFZ.4.4.2024.004")
                manifest["retrievals"].append(record)
            son, rejected, sonqa = normalize_sondoc(args.out / "sondoc_source.csv")
            son.to_csv(args.out / "sondoc_observations.csv", index=False)
            rejected.to_csv(args.out / "sondoc_quarantine.csv", index=False)
            discharge, qqa = normalize_discharge(args.out / "tanchau_discharge_source.csv")
            discharge.to_csv(args.out / "tanchau_discharge_monthly.csv", index=False)
        manifest["sondoc"] = sonqa
        manifest["discharge"] = qqa
        if args.weather_end:
            all_monthly = []
            for station, (lat, lon) in SITES.items():
                params = dict(latitude=lat, longitude=lon, start_date=args.weather_start, end_date=args.weather_end,
                              daily=",".join(WEATHER), timezone="Asia/Ho_Chi_Minh", models="era5",
                              temperature_unit="celsius", precipitation_unit="mm")
                path = args.out / f"era5_{station}_response.json"
                record = download("https://archive-api.open-meteo.com/v1/archive?" + urlencode(params), path)
                record.update(request_parameters=params, license="CC-BY-4.0",
                              citation="ERA5 / Copernicus Climate Change Service, distributed by Open-Meteo; https://open-meteo.com/en/docs/historical-weather-api")
                manifest["retrievals"].append(record)
                payload = json.loads(path.read_text(encoding="utf-8"))
                record["response_metadata"] = {k: v for k, v in payload.items() if k != "daily"}
                daily, monthly = weather_tables(payload, station, args.weather_start, args.weather_end)
                daily.to_csv(args.out / f"era5_{station}_daily.csv", index=False)
                all_monthly.append(monthly)
            combined = pd.concat(all_monthly, ignore_index=True)
            combined.to_csv(args.out / "era5_monthly.csv", index=False)
            master = pd.read_csv(args.master, usecols=["station", "month_start", "conductivity_mS_per_m"])
            merged = combine_targets(combined, master)
            merged.to_csv(args.out / "master_era5_research.csv", index=False)
            registry = json.loads((ROOT / "data/metadata/forecast_sources.json").read_text(encoding="utf-8-sig"))
            for variable in [x[0] for x in WEATHER.values()]:
                registry["variables"][variable].update(metadata_status="ERA5_REQUEST_RESPONSE_UNIT_GRID_TZ_RECORDED",
                    note="Full replacement weather series from explicit ERA5. Monthly aggregates verified; historical issue-time vintages unavailable. Five-day availability remains a retrospective scenario.")
            registry["metadata_findings"]["weather_coordinates"] = {k: [lon, lat] for k, (lat, lon) in SITES.items()}
            registry["metadata_findings"]["weather_daily_to_monthly"] = "See this run's response metadata, full-day coverage checks and ERA5 monthly CSV."
            registry["snapshot_hashes"] = {"master_era5_research.csv": hashlib.sha256((args.out / "master_era5_research.csv").read_bytes()).hexdigest()}
            registry["research_snapshot_manifest"] = "source_manifest.json"
            registry["weather_availability_note"] = "ERA5 fixed model, request and response retained; 5-day historical release assumption, not archived real-time vintages."
            registry["review_date"] = datetime.now(timezone.utc).date().isoformat()
            write_json(args.out / "forecast_sources_era5.json", registry)
            manifest["weather"] = {"monthly_rows": len(combined), "first_month": combined.month_start.min(),
                                   "last_month": combined.month_start.max(), "historical_vintages_certified": False,
                                   "original_master_sha256": hashlib.sha256(args.master.read_bytes()).hexdigest()}
    except Exception as exc:
        manifest["errors"].append({"type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        write_json(args.out / "source_manifest.json", manifest)
    print(json.dumps({"output": str(args.out), "sondoc": manifest["sondoc"], "discharge": manifest["discharge"],
                      "weather": manifest.get("weather")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
