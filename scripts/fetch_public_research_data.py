"""Refresh canonical public sources and optionally download selected ERA5 weather.

Canonical Son Doc/Tan Chau files live under ``data/external/sources``. Each
execution writes only run-specific provenance and weather files under
``data/external/download_runs``; it never imports into PostgreSQL.
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
from urllib.parse import urlencode
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
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_tls_context():
    """Use native certificate validation plus public roots, without global patches."""
    try:
        import certifi
        import truststore
    except ImportError as exc:
        raise RuntimeError(
            "Missing HTTPS dependencies. Run the project Python with "
            "-m pip install -r requirements-forecast-multivariate.txt "
            "(the updated file includes truststore and certifi)."
        ) from exc
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cafile=certifi.where())
    # Optional additional CA file supplied by the user/organisation, never a
    # certificate downloaded from the failing server and silently trusted.
    extra_ca = os.environ.get("WEBGIS_CA_BUNDLE")
    if extra_ca:
        context.load_verify_locations(cafile=extra_ca)
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.set_alpn_protocols(["http/1.1"])
    return context


def download(url, path, expected=None):
    # No credentials, executable content, or third-party serialized models.
    context = create_tls_context()
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
    value = pd.to_numeric(raw.iloc[:, 1].str.strip(), errors="coerce")
    duplicates = when.duplicated(keep=False) & when.notna()
    reasons = []
    for i in range(len(raw)):
        issue = []
        if pd.isna(when.iloc[i]): issue.append("INVALID_TIMESTAMP")
        if duplicates.iloc[i]: issue.append("DUPLICATE_TIMESTAMP_ALL_MEMBERS_QUARANTINED")
        if not np.isfinite(value.iloc[i]): issue.append("MISSING_OR_NONFINITE_SALINITY")
        elif value.iloc[i] < 0: issue.append("NEGATIVE_SALINITY")
        reasons.append(";".join(issue))
    audit = raw.assign(source_data_row=np.arange(1, len(raw) + 1), rejection_reason=reasons)
    ok = audit.rejection_reason.eq("")
    normalized = pd.DataFrame({"observed_at": when[ok].dt.tz_localize("Asia/Ho_Chi_Minh").map(lambda t: t.isoformat()),
                               "salinity_g_per_l": value[ok], "source_data_row": audit.loc[ok, "source_data_row"]})
    normalized["site_code"] = "GFZ_SONDOC"
    normalized["unit"] = "g/L"
    normalized["source_quality"] = "NOT_PROVIDED"
    normalized["time_zone_status"] = "ASSUMED_ASIA_HO_CHI_MINH_NOT_DECLARED_IN_SOURCE"
    normalized = normalized.sort_values("observed_at").reset_index(drop=True)
    qa = {"raw_rows": len(raw), "accepted_rows": int(ok.sum()), "rejected_rows": int((~ok).sum()),
          "duplicate_member_rows": int(duplicates.sum()), "invalid_numeric_rows": int((~np.isfinite(value)).sum()),
          "first_timestamp": normalized.observed_at.min(), "last_timestamp": normalized.observed_at.max(),
          "min_g_per_l": float(value[ok].min()), "max_g_per_l": float(value[ok].max()),
          "time_zone": "ASSUMPTION_ONLY", "publication_vintages_available": False,
          "sampling": "Discontinuous campaigns, generally 2-hour intervals; no interpolation performed.",
          "location_gfz": {"longitude": 106.45747, "latitude": 10.06425},
          "location_warning": "A different 2026 Zenodo dataset locates Son Doc at 106.4999811, 10.0285082. Identity/location unresolved; do not merge by name.",
          "method_warning": "2024 metadata says surface water; 2020 paper describes depth averaging. Measurement protocol needs confirmation.",
          "license": "CC-BY-4.0", "doi": "10.5880/GFZ.4.4.2024.004"}
    return normalized, audit.loc[~ok].copy(), qa


def normalize_discharge(path):
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    start = lines.index("year;month;Q [m3/s]")
    frame = pd.read_csv(io.StringIO("\n".join(lines[start:])), sep=";")
    date = pd.to_datetime({"year": frame.year, "month": frame.month, "day": 1}, errors="raise")
    values = pd.to_numeric(frame["Q [m3/s]"], errors="raise")
    if date.duplicated().any() or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Invalid discharge data.")
    result = pd.DataFrame({"month_start": date.dt.strftime("%Y-%m-%d"), "discharge_m3s": values,
                           "source_kind": np.where(frame.year < 1995, "RECONSTRUCTED_WUP_JICA",
                               np.where(frame.year == 1995, "TRANSITION_YEAR_SOURCE_AMBIGUOUS", "REPORTED_GAUGE_MONTHLY"))})
    result["site_code"] = "GFZ_TANCHAU"
    result["source_quality"] = "NOT_PROVIDED"
    qa = {"rows": len(result), "first_month": result.month_start.min(), "last_month": result.month_start.max(),
          "unit": "m3/s", "unit_evidence": "CSV header and detailed CSV comment; PDF has a conflicting m/s typo.",
          "coverage_evidence": "Actual rows, not the 1964-2017 filename.", "source_counts": result.source_kind.value_counts().to_dict(),
          "publication_vintages_available": False, "license": "CC-BY-4.0", "doi": "10.5880/GFZ.4.4.2024.004"}
    return result, qa


def weather_tables(payload, station, start, end):
    if payload.get("timezone") != "Asia/Ho_Chi_Minh" or payload.get("utc_offset_seconds") != 25200:
        raise ValueError("Unexpected response time zone.")
    frame = pd.DataFrame(payload["daily"])
    dates = pd.to_datetime(frame.time)
    if list(dates) != list(pd.date_range(start, end, freq="D")):
        raise ValueError("Missing, duplicated, unordered or extra weather days.")
    for field, (_, expected, _) in WEATHER.items():
        if payload["daily_units"].get(field) != expected:
            raise ValueError(f"Unexpected unit: {field}.")
        frame[field] = pd.to_numeric(frame[field], errors="raise")
        if not np.isfinite(frame[field]).all():
            raise ValueError("Incomplete weather response; partial months must not be silently aggregated.")
        if expected == "mm" and (frame[field] < 0).any(): raise ValueError("Negative precipitation/ET0.")
    frame["station"] = station
    frame["month_start"] = dates.dt.to_period("M").dt.to_timestamp()
    monthly = []
    for when, group in frame.groupby("month_start"):
        # A partial first/last month remains in the raw daily response only.
        if len(group) != when.days_in_month: continue
        row = {"station": station, "month_start": str(when.date())}
        for field, (name, _, op) in WEATHER.items(): row[name] = float(getattr(group[field], op)())
        monthly.append(row)
    return frame.drop(columns="month_start"), pd.DataFrame(monthly)


def combine_targets(weather, master):
    master = master[["station", "month_start", "conductivity_mS_per_m"]].copy()
    master["station"] = master.station.str.upper().str.replace("_", "", regex=False)
    if not master.station.isin(SITES).all(): raise ValueError("Unknown target station.")
    master["month_start"] = pd.to_datetime(master.month_start).dt.strftime("%Y-%m-%d")
    if master.duplicated(["station", "month_start"]).any(): raise ValueError("Duplicate target month.")
    merged = weather.merge(master, on=["station", "month_start"], how="left", validate="one_to_one")
    for station in weather.station.unique():
        selected_months = weather.loc[weather.station.eq(station), "month_start"]
        expected = master.loc[master.station.eq(station) & master.month_start.isin(selected_months), "conductivity_mS_per_m"].count()
        actual = merged.loc[merged.station.eq(station), "conductivity_mS_per_m"].count()
        if expected == 0 or actual != expected: raise ValueError("Target join lost labels or has no overlap.")
    return merged


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "data/external/download_runs/research_step07")
    parser.add_argument("--sources", type=Path, default=ROOT / "data/external/sources")
    parser.add_argument("--weather-start", default="1985-01-01")
    parser.add_argument("--weather-end", help="Optional completed date, e.g. 2026-09-30. Adds both stations' ERA5.")
    parser.add_argument("--master", type=Path, default=ROOT / "data/archive/legacy_analysis/master_timeseries.csv")
    args = parser.parse_args()
    try:
        args.out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error(f"Output directory already exists: {args.out}. "
                     "Keep it for inspection and choose a new --out directory.")
    manifest = {"schema_version": 1, "retrievals": [], "errors": [], "gate_decision_eligible": False}
    try:
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
