"""Collect public MRC observations along the Tien River with source provenance.

Raw MRC payloads stay separate from derived daily summaries. Never converts
conductivity to salinity or treats water level as discharge.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

import certifi
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.fetch_mrc_public import BASE, INVENTORY, normalize
from scripts.fetch_public_research_data import write_json

DEFAULT = ROOT / "data/external/tien_multisite_20261029"
SUPPLEMENT_DEFAULT = ROOT / "data/external/tien_multisite_supplement_20261029"
HISTORICAL_DEFAULT = ROOT / "data/external/tien_manual_history_20261029"
FULL_MANUAL_DEFAULT = ROOT / "data/external/tien_manual_long_20261029"
EXTENDED_EC_DEFAULT = ROOT / "data/external/tien_ec_extended_20261029"
KRATIE_DEFAULT = ROOT / "data/external/mrc_kratie_discharge_20261029"
RECENT_MANUAL_DEFAULT = ROOT / "data/external/tien_manual_2024_2026_20261029"
WANTED = [
    ("019804", "Conductivity", "Water Quality", "1985-01-01", "2024-01-01"),
    ("988101", "Conductivity", "Water Quality", "1986-01-01", "2004-01-01"),
    ("988109", "Conductivity", "Water Quality", "1986-01-01", "2004-01-01"),
    ("988114", "Conductivity", "Water Quality", "2004-01-01", "2024-01-01"),
    ("019803", "Water Level", "Telemetry", "2019-01-01", "2024-01-01"),
    ("019804", "Water Level", "Telemetry", "2019-01-01", "2024-01-01"),
    ("985203", "Water Level", "Telemetry", "2019-01-01", "2024-01-01"),
    ("019805", "Water Level", "Manual", "1985-01-01", "2013-01-01"),
]
SUPPLEMENT = [
    # Manual levels may fill telemetry gaps, but remain a separate source and datum.
    ("019804", "Water Level", "Manual", "2019-01-01", "2024-01-01"),
    ("985203", "Water Level", "Manual", "2019-01-01", "2024-01-01"),
    ("980601", "Water Level", "Manual", "2019-01-01", "2024-01-01"),
    ("980601", "Water Level", "Telemetry", "2019-01-01", "2027-01-01"),
    ("019803", "Water Level", "Telemetry", "2024-01-01", "2027-01-01"),
    ("019804", "Water Level", "Telemetry", "2024-01-01", "2027-01-01"),
    ("985203", "Water Level", "Telemetry", "2024-01-01", "2027-01-01"),
]
HISTORICAL = [
    ("019804", "Water Level", "Manual", "2008-01-01", "2019-01-01"),
    ("985203", "Water Level", "Manual", "2008-01-01", "2019-01-01"),
    ("980601", "Water Level", "Manual", "2008-01-01", "2019-01-01"),
]
FULL_MANUAL = [
    ("019803", "Water Level", "Manual", "1985-01-01", "2024-01-01"),
    ("019804", "Water Level", "Manual", "1985-01-01", "2008-01-01"),
    ("985203", "Water Level", "Manual", "1992-01-01", "2008-01-01"),
    ("980601", "Water Level", "Manual", "1992-01-01", "2008-01-01"),
]
EXTENDED_EC = [
    ("988103", "Conductivity", "Water Quality", "1986-01-01", "2004-01-01"),
    ("988104", "Conductivity", "Water Quality", "1986-01-01", "2004-01-01"),
    ("988108", "Conductivity", "Water Quality", "1986-01-01", "2004-01-01"),
    ("039803", "Conductivity", "Water Quality", "1985-01-01", "2024-01-01"),
]
KRATIE = [("014901", "Discharge", "Calculated daily discharge", "1985-01-01", "2027-01-01")]
RECENT_MANUAL = [("019803", "Water Level", "Manual", "2024-01-01", "2027-01-01")]


def download(url, path):
    """Use verified HTTPS without the optional truststore dependency."""
    if urlsplit(url).scheme != "https" or urlsplit(url).hostname != "timeseries.api.mrcmekong.org":
        raise ValueError("Unexpected MRC download host")
    context = ssl.create_default_context(cafile=certifi.where())
    with urlopen(Request(url, headers={"User-Agent": "WebGIS-academic-data-review/1.0"}),
                 timeout=55, context=context) as response:
        blob = response.read(20_000_001)
        final_url = response.url
    if len(blob) > 20_000_000 or urlsplit(final_url).hostname != "timeseries.api.mrcmekong.org":
        raise ValueError("Large response or unexpected redirect")
    path.write_bytes(blob)
    return dict(url=url, final_url=final_url, file=path.name, bytes=len(blob),
                sha256=hashlib.sha256(blob).hexdigest(),
                fetched_at=datetime.now(timezone.utc).isoformat())


def periods(start, end, chunk_years):
    if not chunk_years:
        yield pd.Timestamp(start), pd.Timestamp(end) - pd.Timedelta(seconds=1)
        return
    for year in range(pd.Timestamp(start).year, pd.Timestamp(end).year, chunk_years):
        lo = max(pd.Timestamp(start), pd.Timestamp(f"{year}-01-01"))
        hi = min(pd.Timestamp(end), pd.Timestamp(f"{year+chunk_years}-01-01")) - pd.Timedelta(seconds=1)
        yield lo, hi


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["core", "supplement", "historical", "full_manual", "extended_ec", "kratie", "recent_manual"], default="core")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.out is None:
        args.out = {"core": DEFAULT, "supplement": SUPPLEMENT_DEFAULT,
                    "historical": HISTORICAL_DEFAULT, "full_manual": FULL_MANUAL_DEFAULT,
                    "extended_ec": EXTENDED_EC_DEFAULT, "kratie": KRATIE_DEFAULT,
                    "recent_manual": RECENT_MANUAL_DEFAULT}[args.profile]
    wanted = {"core": WANTED, "supplement": SUPPLEMENT,
              "historical": HISTORICAL, "full_manual": FULL_MANUAL,
              "extended_ec": EXTENDED_EC, "kratie": KRATIE,
              "recent_manual": RECENT_MANUAL}[args.profile]
    args.out.mkdir(parents=True, exist_ok=False)
    manifest = dict(retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                    source=INVENTORY, license_status="Public API; verify reuse terms before redistribution",
                    source_qa="Keep MRC grades and approvals; no automatic promotion",
                    series=[], downloads=[], errors=[])
    try:
        receipt = download(INVENTORY, args.out / "inventory.json")
        manifest["downloads"].append(receipt)
        inventory = json.loads((args.out / "inventory.json").read_text(encoding="utf-8"))
        for station, parameter, label, start, end in wanted:
            matches = [x for x in inventory if x["stationCode"] == station
                       and x["parameter"] == parameter and x["label"] == label]
            if len(matches) != 1:
                raise ValueError(f"Expected one series for {station} {parameter} {label}: {len(matches)}")
            meta = matches[0]
            name = f"{station}_{parameter.replace(' ', '_')}_{label}_{meta['uniqueId'][:8]}"
            chunks = []
            chunk_years = (1 if label == "Telemetry" else 5 if args.profile in ("full_manual", "kratie") else None)
            for lo, hi in periods(start, end, chunk_years):
                sd = lo.tz_localize("Asia/Ho_Chi_Minh").tz_convert("UTC").isoformat()
                ed = hi.tz_localize("Asia/Ho_Chi_Minh").tz_convert("UTC").isoformat()
                url = BASE + "ts/data/timeSeriesCorrectedData/" + meta["uniqueId"] + "?" + urlencode({"sd": sd, "ed": ed})
                suffix = f"_{lo.year}" if chunk_years else ""
                raw = args.out / f"{name}{suffix}.json"
                manifest["downloads"].append(download(url, raw))
                payload = json.loads(raw.read_text(encoding="utf-8"))
                frame, rejected = normalize(payload, meta)
                if len(rejected):
                    rejected.to_csv(args.out / f"{name}{suffix}_quarantine.csv", index=False)
                chunks.append(frame)
                print(name, lo.year, len(frame), "rejected", len(rejected), flush=True)
            all_rows = pd.concat(chunks, ignore_index=True)
            if all_rows.duplicated("observed_at").any():
                raise ValueError(f"Duplicate timestamps after stitching {name}")
            all_rows.to_csv(args.out / f"{name}.csv", index=False, encoding="utf-8-sig")
            if parameter == "Water Level" and len(all_rows):
                daily = all_rows.copy()
                daily["date_local"] = pd.to_datetime(daily.observed_at).dt.date
                daily = daily.groupby("date_local").agg(n=("value", "size"),
                    level_mean_m=("value", "mean"), level_min_m=("value", "min"),
                    level_max_m=("value", "max")).reset_index()
                daily.to_csv(args.out / f"{name}_daily.csv", index=False, encoding="utf-8-sig")
            manifest["series"].append(dict(file=f"{name}.csv", unique_id=meta["uniqueId"],
                station_code=station, station_name=meta["stationName"], parameter=parameter,
                label=label, unit=meta["unit"], latitude=meta["latitude"], longitude=meta["longitude"],
                source_first=meta["correctedStartTime"], source_last=meta["correctedEndTime"],
                downloaded_rows=len(all_rows), first_observed=all_rows.observed_at.min() if len(all_rows) else None,
                last_observed=all_rows.observed_at.max() if len(all_rows) else None,
                extracted_sha256=hashlib.sha256((args.out / f"{name}.csv").read_bytes()).hexdigest(),
                note="Date windows are inclusive; publication vintage unknown; no imputation"))
    except Exception as exc:
        manifest["errors"].append(dict(type=type(exc).__name__, message=str(exc)))
        raise
    finally:
        write_json(args.out / "manifest.json", manifest)


if __name__ == "__main__":
    main()
