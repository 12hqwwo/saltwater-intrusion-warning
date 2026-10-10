"""Public MRC inventory and observations, keeping source QA and separate series.

No login, portal chart key or private API is used. Never writes to PostgreSQL.
The JSON routes are used by the public portal; they are not a promised stable API.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
import pandas as pd

try:
    from scripts.fetch_public_research_data import download, write_json
except ModuleNotFoundError:
    from fetch_public_research_data import download, write_json

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://timeseries.api.mrcmekong.org/api/v1/"
INVENTORY = BASE + "ts/inventory/timeSeriesList"
UNITS = {"Conductivity": "mS/m", "Water Temperature": "degC", "Water Level": "m"}


def instant(value):
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None: raise ValueError("MRC timestamp lacks UTC offset.")
    return t


def active_values(payload, group, key, when):
    return [r.get(key) for r in payload.get(group, [])
            if instant(r["StartTime"]) <= when <= instant(r["EndTime"])]


def normalize(payload, metadata):
    for key, expected in [("UniqueId", metadata["uniqueId"]), ("Parameter", metadata["parameter"]),
                          ("Unit", metadata["unit"]), ("Label", metadata["label"]),
                          ("LocationIdentifier", metadata["locationIdentifier"])]:
        if payload.get(key) != expected: raise ValueError(f"Series response mismatch: {key}.")
    if metadata["unit"] != UNITS[metadata["parameter"]]: raise ValueError("Unsupported unit.")
    points = payload["Points"]
    if int(payload["NumPoints"]) != len(points): raise ValueError("Reported point count mismatch.")
    timestamps = [instant(p["Timestamp"]) for p in points]
    duplicates = pd.Index(timestamps).duplicated(keep=False)
    result, rejected = [], []
    for n, (point, when) in enumerate(zip(points, timestamps)):
        value = point["Value"]["Numeric"]
        reasons = []
        if duplicates[n]: reasons.append("DUPLICATE_TIMESTAMP")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            reasons.append("NONFINITE_OR_MISSING_VALUE")
        elif metadata["parameter"] == "Conductivity" and value < 0: reasons.append("NEGATIVE_CONDUCTIVITY")
        if reasons:
            rejected.append({"source_point_index":n, "timestamp":point["Timestamp"], "reasons":";".join(reasons)})
            continue
        result.append(dict(site_code="MRC_VN_" + metadata["stationCode"], unique_id=metadata["uniqueId"],
            parameter=metadata["parameter"], series_label=metadata["label"], observed_at=when.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(),
            value=value, unit=metadata["unit"], quality_flag="UNVERIFIED",
            source_approvals=json.dumps(active_values(payload,"Approvals","LevelDescription",when),ensure_ascii=False),
            source_grades=json.dumps(active_values(payload,"Grades","GradeCode",when)),
            source_methods=json.dumps(active_values(payload,"Methods","MethodCode",when)),
            source_qualifiers=json.dumps([r for r in payload.get("Qualifiers",[]) if instant(r["StartTime"]) <= when <= instant(r["EndTime"])],ensure_ascii=False),
            source_notes=json.dumps(active_values(payload,"Notes","NoteText",when),ensure_ascii=False),
            publication_time_known=False, ec_temperature_basis="UNKNOWN" if metadata["parameter"]=="Conductivity" else "NOT_APPLICABLE"))
    frame = pd.DataFrame(result)
    if len(frame): frame = frame.sort_values("observed_at").reset_index(drop=True)
    return frame, pd.DataFrame(rejected)


def paired_ec_temperature(ec, water):
    columns = ["site_code", "observed_at", "value", "unique_id", "source_approvals", "source_grades", "source_notes"]
    left = ec[columns].rename(columns={k:("ec_"+k if k not in ("site_code","observed_at") else k) for k in columns})
    right = water[columns].rename(columns={k:("water_temperature_"+k if k not in ("site_code","observed_at") else k) for k in columns})
    result = left.merge(right,on=["site_code","observed_at"],how="inner",validate="one_to_one")
    result.rename(columns={"ec_value":"ec_mS_per_m","water_temperature_value":"water_temperature_degC"},inplace=True)
    result["ec_temperature_basis"] = "UNKNOWN"
    result["salinity_conversion_eligible"] = False
    result["note"] = "Exact timestamp match is not proof of the same sample or of EC temperature compensation."
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=ROOT/"data/external/mrc_step07")
    parser.add_argument("--hydrology-from",default="2026-09-01")
    parser.add_argument("--hydrology-until",help="ISO timestamp with offset; default is retrieval start time in UTC.")
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    now=datetime.now(timezone.utc)
    until=instant(args.hydrology_until) if args.hydrology_until else now
    start=instant(args.hydrology_from+"T00:00:00+07:00")
    if not start < until <= now:raise ValueError("Hydrology window must end no later than now.")
    manifest={"schema_version":1,"retrievals":[],"series":[],"errors":[],"gate_decision_eligible":False,
              "license_status":"Publicly accessible; no dataset-specific reuse license confirmed.",
              "quality_policy":"Keep Working, grade -1, notes and qualifiers. Never promote to VALIDATED.",
              "api_stability":"Public portal JSON endpoints; no service-level or long-term compatibility guarantee."}
    try:
        manifest["retrievals"].append(download(INVENTORY,args.out/"inventory.json"))
        inventory=json.loads((args.out/"inventory.json").read_text())
        selected=[r for r in inventory if r["stationCode"] in ("019803","019805") and
                  (r["parameter"] in ("Conductivity","Water Temperature") or
                   (r["stationCode"]=="019803" and r["parameter"]=="Water Level" and r["label"] in ("Manual","Telemetry")))]
        write_json(args.out/"selected_series_metadata.json",selected)
        frames=[]
        for series in selected:
            # Unique ID and acquisition label prevent manual/telemetry overwrites.
            name=series["stationCode"]+"_"+series["parameter"].replace(" ","_")+"_"+series["label"].replace(" ","_")+"_"+series["uniqueId"][:8]
            if series["parameter"]=="Water Level":sd,ed=start,until
            else:sd,ed=instant(series["correctedStartTime"]),instant(series["correctedEndTime"])
            url=BASE+"ts/data/timeSeriesCorrectedData/"+series["uniqueId"]+"?"+urlencode({"sd":sd.astimezone(timezone.utc).isoformat(),"ed":ed.astimezone(timezone.utc).isoformat()})
            provenance=download(url,args.out/(name+".json"));manifest["retrievals"].append(provenance)
            payload=json.loads((args.out/(name+".json")).read_text())
            frame,rejected=normalize(payload,series)
            if len(frame) and any(instant(t)<sd or instant(t)>ed for t in frame.observed_at):raise ValueError("API returned out-of-window points.")
            frame.to_csv(args.out/(name+".csv"),index=False)
            if len(rejected):rejected.to_csv(args.out/(name+"_quarantine.csv"),index=False)
            frames.append(frame)
            summary=dict(file=name+".csv",unique_id=series["uniqueId"],station_code=series["stationCode"],parameter=series["parameter"],
                label=series["label"],unit=series["unit"],rows=len(frame),rejected_rows=len(rejected),
                first=frame.observed_at.min() if len(frame) else None,last=frame.observed_at.max() if len(frame) else None,
                source_metadata=series,methods=payload.get("Methods",[]),approvals=payload.get("Approvals",[]),
                grades=payload.get("Grades",[]),notes=payload.get("Notes",[]))
            if len(frame)>1:
                gaps=pd.to_datetime(frame.observed_at,utc=True).diff().dt.total_seconds().dropna()/60
                summary["sampling_audit"]={"median_gap_minutes":float(gaps.median()),"max_gap_minutes":float(gaps.max()),
                    "gaps_exceeding_15_minutes":int((gaps>15).sum()) if series["label"]=="Telemetry" else None,
                    "gap_minutes_histogram":{str(k):int(v) for k,v in gaps.value_counts().sort_index().items()}}
            if len(frame):summary["numeric_range"]={"min":float(frame.value.min()),"max":float(frame.value.max())}
            manifest["series"].append(summary)
            print(series["identifier"],len(frame),summary["last"],flush=True)
        all_data=pd.concat(frames,ignore_index=True)
        ec=all_data.loc[all_data.parameter.eq("Conductivity")]
        water=all_data.loc[all_data.parameter.eq("Water Temperature")]
        paired=paired_ec_temperature(ec,water)
        paired.to_csv(args.out/"ec_water_temperature_pairs.csv",index=False)
        manifest["exact_timestamp_pairs"]=paired.groupby("site_code").size().to_dict()
        manifest["conversion_status"]="BLOCKED_EC_COMPENSATION_BASIS_AND_SAMPLE_PROTOCOL_UNCONFIRMED"
    except Exception as exc:
        manifest["errors"].append({"type":type(exc).__name__,"message":str(exc)})
        raise
    finally:write_json(args.out/"source_manifest.json",manifest)
    print(args.out)


if __name__=="__main__":main()
