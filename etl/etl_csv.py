"""CSV -> validation/reject -> normalized CSV -> transactional SQL -> optional psql.

Python 3.9+, standard library only. Supports the supplied MRC EC exports and
master_timeseries.csv. Default mode never connects to the database.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import re
import subprocess
import sys
import uuid
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

RAW_HEADERS = ["Country Code", "Station Code", "Parameter", "Label",
               "Timestamp (UTC+07:00)", "Value", "Unit", "Observed or Estimated",
               "Approval Level", "Grade"]
FEATURES = ["conductivity_ms_per_m", "precipitation_sum", "temperature_mean",
            "temperature_max", "temperature_min", "evapotranspiration_sum",
            "windspeed_mean", "humidity_mean", "shortwave_rad_sum",
            "water_level_m", "glofas_discharge_m3s"]
MASTER_HEADERS = ["station", "month_start", "conductivity_mS_per_m"] + FEATURES[1:]
SITES = {
    "019803": ("TANCHAU", "Tân Châu - MRC"),
    "019805": ("MYTHO", "Mỹ Tho - MRC"),
}
AREAS = {"TanChau": "TANCHAU", "MyTho": "MYTHO"}
RAW_COLUMNS = ["source_row", "observed_at", "conductivity_ms_per_m", "unit",
               "source_label", "observed_or_estimated", "approval_level", "grade"]
MASTER_COLUMNS = ["source_row", "area_code", "month_start"] + FEATURES


def number(value, optional=False, nonnegative=False):
    if optional and value.strip().lower() in ("", "na", "nan", "null", "none"):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError("NOT_NUMERIC")
    if not math.isfinite(result):
        raise ValueError("NOT_FINITE")
    if nonnegative and result < 0:
        raise ValueError("NEGATIVE_VALUE")
    return result


def normalize(raw, source_row, kind, station):
    if None in raw or any(v is None for v in raw.values()):
        raise ValueError("COLUMN_COUNT")
    if any("\x00" in v for v in raw.values()):
        raise ValueError("NUL_CHARACTER")
    if kind == "raw":
        if raw["Country Code"] != "VN" or raw["Station Code"] != station:
            raise ValueError("STATION_MISMATCH")
        if raw["Parameter"] != "Conductivity" or raw["Unit"] != "mS/m":
            raise ValueError("PARAMETER_OR_UNIT_MISMATCH")
        try:
            stamp = datetime.fromisoformat(raw["Timestamp (UTC+07:00)"])
        except ValueError:
            raise ValueError("INVALID_TIMESTAMP")
        if stamp.utcoffset() != timedelta(hours=7):
            raise ValueError("EXPECTED_UTC_PLUS_07")
        if raw["Observed or Estimated"] not in ("O", "E"):
            raise ValueError("INVALID_O_E")
        for field in ("Label", "Approval Level", "Grade"):
            if not raw[field].strip():
                raise ValueError("EMPTY_" + field.replace(" ", "_"))
        item = dict(zip(RAW_COLUMNS, [source_row, stamp.isoformat(),
                    number(raw["Value"], nonnegative=True), "mS/m", raw["Label"],
                    raw["Observed or Estimated"], raw["Approval Level"], raw["Grade"]]))
        key = (station, stamp.isoformat())
    else:
        if raw["station"] not in AREAS:
            raise ValueError("UNKNOWN_AREA")
        try:
            month = date.fromisoformat(raw["month_start"])
        except ValueError:
            raise ValueError("INVALID_MONTH")
        if month.day != 1:
            raise ValueError("MONTH_MUST_START_ON_DAY_1")
        item = {"source_row": source_row, "area_code": AREAS[raw["station"]],
                "month_start": month.isoformat()}
        nonnegative = {"conductivity_ms_per_m", "precipitation_sum",
                       "evapotranspiration_sum", "windspeed_mean",
                       "shortwave_rad_sum", "glofas_discharge_m3s"}
        for field in FEATURES:
            original = "conductivity_mS_per_m" if field == FEATURES[0] else field
            try:
                item[field] = number(raw[original], optional=True,
                                     nonnegative=field in nonnegative)
            except ValueError as exc:
                raise ValueError(field + ":" + str(exc))
        humidity = item["humidity_mean"]
        if humidity is not None and not 0 <= humidity <= 100:
            raise ValueError("HUMIDITY_OUT_OF_RANGE")
        lo, avg, hi = (item[k] for k in ("temperature_min", "temperature_mean", "temperature_max"))
        if ((lo is not None and avg is not None and lo > avg) or
            (avg is not None and hi is not None and avg > hi) or
            (lo is not None and hi is not None and lo > hi)):
            raise ValueError("TEMPERATURE_ORDER")
        key = (item["area_code"], item["month_start"])
    return item, key


def validate(content, kind, station=None):
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""), strict=True)
    expected = RAW_HEADERS if kind == "raw" else MASTER_HEADERS
    if reader.fieldnames != expected:
        raise ValueError("HEADER_MISMATCH: expected " + repr(expected) + "; got " + repr(reader.fieldnames))
    prepared, rejects, total = [], [], 0
    for row_number, raw in enumerate(reader, start=2):
        total += 1
        try:
            item, key = normalize(raw, row_number, kind, station)
            prepared.append((item, key, raw))
        except ValueError as exc:
            rejects.append({"source_row": row_number, "reason": str(exc),
                            "raw_json": json.dumps(raw, ensure_ascii=False)})
    counts = Counter(key for _, key, _ in prepared)
    accepted = []
    for item, key, raw in prepared:
        if counts[key] > 1:
            rejects.append({"source_row": item["source_row"], "reason": "DUPLICATE_KEY_ALL_ROWS_REJECTED",
                            "raw_json": json.dumps(raw, ensure_ascii=False)})
        else:
            accepted.append(item)
    return accepted, sorted(rejects, key=lambda x: x["source_row"]), total


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def make_sql(rows, kind, station, filename, digest, database):
    """All identifiers are fixed; variable data is escaped as SQL literals."""
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", database):
        raise ValueError("Database name must contain lowercase letters, digits and underscores")
    count = len(rows)
    raw = kind == "raw"
    source = "MRC_WATER_QUALITY" if raw else "LEGACY_MONTHLY_PIPELINE"
    source_type = "OFFICIAL" if raw else "RESEARCH"
    source_name = "MRC Water Quality - user supplied export" if raw else "User monthly research pipeline"
    reference = ("Original MRC CSV provided by the user; quality flags retained" if raw else
                 "master_timeseries.csv provided by the user; aggregation not fully verified")
    dataset_kind = "RAW_EC" if raw else "MONTHLY_FEATURES"
    product = "IN_SITU_OBSERVATION" if raw else "MIXED_DERIVED"
    code = ("MRC_EC_" + SITES[station][0] if raw else "MASTER") + "_" + digest[:16]
    metadata = {
        "etl_version": "week05_csv_v1", "unit" if raw else "conductivity_unit": "mS/m",
        "source_timezone": "UTC+07:00" if raw else "MONTH_DATE",
        "source_row_definition": "CSV record number including header; not physical line with multiline fields",
        "salinity_conversion_performed": False, "operational_gate_decision_ready": False,
    }
    if raw:
        metadata.update(temperature_reference="UNKNOWN", quality="Original flags retained; internal quality UNVERIFIED")
    else:
        metadata.update(water_level_vertical_datum="UNKNOWN", meteo_units="UNVERIFIED",
                        glofas_spatial_extraction="LEGACY_SPATIAL_MEAN_UNVERIFIED",
                        windspeed_mean_semantics="Legacy name; mean of daily maximum in supplied pipeline",
                        pipeline="Imported supplied master snapshot; upstream feature reconstruction not performed")
    columns = RAW_COLUMNS if raw else MASTER_COLUMNS
    types = {"source_row": "integer", "observed_at": "timestamptz", "month_start": "date"}
    definitions = ", ".join(c + " " + types.get(c, "double precision" if c in FEATURES else "text") for c in columns)
    parts = [f"""-- Generated ETL: {code}. Entire file is one transaction.
-- Existing matching snapshot: verify all source values, insert zero observations.
-- Any mismatch/error: transaction is rolled back; no silent repair/overwrite.
BEGIN;
SET LOCAL client_encoding = 'UTF8';
SET LOCAL standard_conforming_strings = on;
SET LOCAL TIME ZONE 'Asia/Ho_Chi_Minh';
SET LOCAL search_path = public, pg_catalog;
SET LOCAL lock_timeout = '10s';
DO $guard$ BEGIN
 IF current_database() <> {literal(database)} THEN
   RAISE EXCEPTION 'Wrong database; expected {database}';
 END IF;
END $guard$;
LOCK TABLE public.source_dataset IN SHARE ROW EXCLUSIVE MODE;
CREATE TEMP TABLE etl_input ON COMMIT DROP AS
SELECT * FROM jsonb_to_recordset({literal(json.dumps(rows, ensure_ascii=False, allow_nan=False))}::jsonb)
AS r({definitions});
INSERT INTO public.data_source(source_code,source_name,source_type,reference,is_demo)
VALUES ({literal(source)},{literal(source_name)},{literal(source_type)},{literal(reference)},false)
ON CONFLICT(source_code) DO NOTHING;
DO $guard$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.data_source WHERE source_code={literal(source)}
                AND source_type={literal(source_type)} AND is_demo=false) THEN
   RAISE EXCEPTION 'Source identity mismatch';
 END IF;
END $guard$;
INSERT INTO public.analysis_area(area_code,area_name,scope_note) VALUES
('TANCHAU','Tân Châu','Logical analysis area; sources are not assumed co-located'),
('MYTHO','Mỹ Tho','Logical analysis area; sources are not assumed co-located')
ON CONFLICT(area_code) DO NOTHING;"""]
    if raw:
        area, name = SITES[station]
        site_code = "MRC_VN_" + station
        parts.append(f"""
INSERT INTO public.measurement_site(site_code,source_id,country_code,external_site_code,site_name,area_id)
SELECT {literal(site_code)},s.source_id,'VN',{literal(station)},{literal(name)},a.area_id
FROM public.data_source s CROSS JOIN public.analysis_area a
WHERE s.source_code={literal(source)} AND a.area_code={literal(area)}
ON CONFLICT(site_code) DO NOTHING;
DO $guard$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.measurement_site m
   JOIN public.data_source s USING(source_id) JOIN public.analysis_area a USING(area_id)
   WHERE m.site_code={literal(site_code)} AND m.external_site_code={literal(station)}
     AND m.country_code='VN' AND NOT m.is_demo
     AND s.source_code={literal(source)} AND a.area_code={literal(area)}) THEN
   RAISE EXCEPTION 'Site identity/area mismatch';
 END IF;
END $guard$;""")
    parts.append(f"""
CREATE TEMP TABLE etl_previous ON COMMIT DROP AS
SELECT dataset_id FROM public.source_dataset WHERE sha256={literal(digest)};
INSERT INTO public.source_dataset(dataset_code,source_id,dataset_kind,data_product_kind,
                                  source_filename,sha256,source_row_count,metadata)
SELECT {literal(code)},s.source_id,{literal(dataset_kind)},{literal(product)},
       {literal(filename)},{literal(digest)},{count},{literal(json.dumps(metadata, ensure_ascii=False))}::jsonb
FROM public.data_source s WHERE s.source_code={literal(source)}
AND NOT EXISTS(SELECT 1 FROM etl_previous);
DO $guard$ BEGIN
 IF NOT EXISTS(SELECT 1 FROM public.source_dataset d JOIN public.data_source s USING(source_id)
  WHERE d.sha256={literal(digest)} AND d.dataset_kind={literal(dataset_kind)}
    AND d.data_product_kind={literal(product)} AND d.source_row_count={count}
    AND s.source_code={literal(source)} AND NOT d.is_demo) THEN
   RAISE EXCEPTION 'Dataset metadata mismatch';
 END IF;
END $guard$;""")
    if raw:
        destination = "conductivity_observation"
        compare_columns = ["site_code"] + RAW_COLUMNS
        insert_columns = ["dataset_id", "source_id", "site_id"] + RAW_COLUMNS
        selected = ["d.dataset_id", "d.source_id", "m.site_id"] + ["i." + c for c in RAW_COLUMNS]
        parts.append(f"""
INSERT INTO public.conductivity_observation({','.join(insert_columns)})
SELECT {','.join(selected)} FROM etl_input i
CROSS JOIN public.source_dataset d CROSS JOIN public.measurement_site m
WHERE d.sha256={literal(digest)} AND m.site_code={literal(site_code)}
AND NOT EXISTS(SELECT 1 FROM etl_previous);
CREATE TEMP VIEW etl_expected AS
SELECT {literal(site_code)}::text AS site_code, {','.join('i.'+c for c in RAW_COLUMNS)} FROM etl_input i;
CREATE TEMP VIEW etl_actual AS
SELECT m.site_code::text, {','.join('o.'+c for c in RAW_COLUMNS)}
FROM public.conductivity_observation o JOIN public.measurement_site m USING(site_id)
JOIN public.source_dataset d USING(dataset_id) WHERE d.sha256={literal(digest)};""")
    else:
        destination = "monthly_feature"
        insert_columns = ["dataset_id", "area_id", "source_row", "month_start"] + FEATURES
        selected = ["d.dataset_id", "a.area_id", "i.source_row", "i.month_start"] + ["i." + c for c in FEATURES]
        parts.append(f"""
INSERT INTO public.monthly_feature({','.join(insert_columns)})
SELECT {','.join(selected)} FROM etl_input i
JOIN public.analysis_area a USING(area_code) CROSS JOIN public.source_dataset d
WHERE d.sha256={literal(digest)} AND NOT EXISTS(SELECT 1 FROM etl_previous);
CREATE TEMP VIEW etl_expected AS SELECT {','.join(MASTER_COLUMNS)} FROM etl_input;
CREATE TEMP VIEW etl_actual AS
SELECT o.source_row,a.area_code::text,o.month_start,{','.join('o.'+c for c in FEATURES)}
FROM public.monthly_feature o JOIN public.analysis_area a USING(area_id)
JOIN public.source_dataset d USING(dataset_id) WHERE d.sha256={literal(digest)};""")
    parts.append(f"""
DO $guard$ BEGIN
 IF (SELECT count(*) FROM etl_actual) <> {count}
    OR EXISTS(SELECT * FROM etl_expected EXCEPT SELECT * FROM etl_actual)
    OR EXISTS(SELECT * FROM etl_actual EXCEPT SELECT * FROM etl_expected) THEN
   RAISE EXCEPTION 'Snapshot content mismatch; rolled back. Check existing rows, no automatic overwrite.';
 END IF;
END $guard$;
SELECT json_build_object('dataset_code',d.dataset_code,'sha256',d.sha256,
 'table',{literal(destination)},'source_rows',{count},'verified_rows',(SELECT count(*) FROM etl_actual),
 'inserted_rows',CASE WHEN EXISTS(SELECT 1 FROM etl_previous) THEN 0 ELSE {count} END,
 'unchanged_rows',CASE WHEN EXISTS(SELECT 1 FROM etl_previous) THEN {count} ELSE 0 END
) AS etl_result FROM public.source_dataset d WHERE d.sha256={literal(digest)};
DROP VIEW etl_actual;
DROP VIEW etl_expected;
COMMIT;
""")
    return "\n".join(parts)


def write_csv(path, rows, columns):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["raw", "master"])
    parser.add_argument("file", type=Path)
    parser.add_argument("--station", choices=sorted(SITES))
    parser.add_argument("--db", required=True, help="Exact target database name; embedded in SQL guard")
    parser.add_argument("--out", type=Path, default=Path("runs"))
    parser.add_argument("--load", action="store_true", help="Run generated SQL using psql; writes to the named database")
    parser.add_argument("--psql", default="psql")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--user", default="postgres")
    args = parser.parse_args()
    if args.kind == "raw" and not args.station:
        parser.error("raw requires --station")
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", args.db):
        parser.error("--db must contain lowercase letters, digits and underscores")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    run = args.out / run_id
    run.mkdir(parents=True, exist_ok=False)
    report = {"run_id": run_id, "input": str(args.file), "database": args.db,
              "kind": args.kind, "mode": "load" if args.load else "prepare",
              "status": "STARTED", "inserted_rows": None}
    exit_code = 0
    try:
        content = args.file.read_bytes()
        report["sha256"] = hashlib.sha256(content).hexdigest()
        rows, rejects, total = validate(content, args.kind, args.station)
        report.update(source_rows=total, valid_rows=len(rows), rejected_rows=len(rejects))
        write_csv(run / "rejects.csv", rejects, ["source_row", "reason", "raw_json"])
        write_csv(run / "normalized.csv", rows, RAW_COLUMNS if args.kind == "raw" else MASTER_COLUMNS)
        if rejects or not rows:
            report["status"] = "REJECTED_NO_DATABASE_WRITE"
            exit_code = 2
        else:
            sql_path = run / "load.sql"
            sql_path.write_text(make_sql(rows, args.kind, args.station, args.file.name,
                                report["sha256"], args.db), encoding="utf-8")
            report["status"] = "READY_SQL_NOT_LOADED"
            if args.load:
                command = [args.psql, "-X", "--set=ON_ERROR_STOP=1", "--pset=pager=off",
                           "--host=" + args.host, "--port=" + str(args.port), "--username=" + args.user,
                           "--dbname=" + args.db, "--file=" + str(sql_path), "--log-file=" + str(run / "database.log")]
                # psql owns the password prompt; no password in this script or its logs.
                result = subprocess.run(command, check=False)
                report["psql_exit_code"] = result.returncode
                if result.returncode == 0:
                    report["status"] = "COMMITTED"
                else:
                    # If connection is lost around COMMIT, outcome is not always knowable.
                    report["status"] = "LOAD_FAILED_VERIFY_DATABASE_BEFORE_RETRY"
                    exit_code = 3
                report["database_result"] = "See database.log etl_result; counts not inferred from validation"
    except (OSError, ValueError, csv.Error, UnicodeError) as exc:
        report["status"] = "FAILED"
        report["error"] = str(exc)
        exit_code = 1
    finally:
        (run / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"run_directory": str(run), **report}, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
