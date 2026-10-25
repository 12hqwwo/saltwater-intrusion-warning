"""Append the current 50-row RIA2 workspace snapshot; dry run unless --apply.

The earlier 40-row recovery import is retained unchanged as a provenance artifact.
"""

import argparse
import csv
import hashlib
import io
import json
import math
import sys
import urllib.request
import urllib.error
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from psycopg import sql
from psycopg.types.json import Jsonb

from backend.database import read_connection
from backend.domain.workspace import validate_bundle
from run_webgis import load_local_env

SOURCE_CODE = "RIA2_CATFISH_MONITORING"
DIRECTORY = ROOT / "data/external/ec_recovery_20261011"
CSV_NAME = "ec_dongthap_ria2_2025.csv"
LOCAL_TZ = timezone(timedelta(hours=7))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_legacy_snapshot():
    manifest_path = DIRECTORY / "ec_recovery_manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    raw = (DIRECTORY / CSV_NAME).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    expected = next(item for item in manifest["datasets"] if item["file"] == CSV_NAME)
    require(digest == expected["sha256"] and len(raw) == expected["bytes"], "CSV hash/size mismatch")
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    sources = {item["source_id"]: item for item in manifest["sources"]}
    for source in sources.values():
        document = (DIRECTORY / source["file"]).read_bytes()
        require(hashlib.sha256(document).hexdigest() == source["sha256"], "Bulletin hash mismatch")
    require(len(rows) == 40 and len(sources) == 4, "Expected 40 observations from four bulletins")
    require(len({(r["site_code"], r["observed_date"]) for r in rows}) == 40, "Duplicate observation identity")
    sites = {}
    for row in rows:
        source = sources[row["source_id"]]
        require(row["source_sha256"] == source["sha256"], "Row/document provenance mismatch")
        require(row["source_file_url"] == source["url"], "Row/document URL mismatch")
        require(row["time_precision"] == "DATE_ONLY", "Unexpected temporal precision")
        require(row["coordinate_crs"] == "NOT_STATED_IN_BULLETIN", "Review coordinate handling first")
        require(date.fromisoformat(row["observed_date"]).isoformat() == row["observed_date"], "Invalid ISO date")
        value = float(row["conductivity_mS_per_m"])
        require(math.isfinite(value) and value >= 0, "Invalid conductivity")
        require(math.isclose(value, float(row["ec_uS_per_cm"]) * 0.1), "Unit conversion mismatch")
        require(bool(row["source_locator"]), "Missing source row locator")
        identity = (row["site_name_source"], row["latitude_source"], row["longitude_source"])
        require(sites.setdefault(row["site_code"], identity) == identity, "Inconsistent station identity")
    require(len(sites) == 10, "Expected ten physical station identities")
    for source in sources.values():
        require(sum(r["source_id"] == source["source_id"] for r in rows) == source["selected_rows"], "Bulletin row count mismatch")
    metadata = {
        "manifest": manifest,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "time_precision": "DATE_ONLY",
        "timestamp_storage_warning": "observed_at is the reported ISO date at 00:00:00+07:00 for storage only; no sampling hour is known. Do not interpret it as an observed instant.",
        "coordinate_warning": "Source CRS is not stated; reported coordinates are retained only in metadata. All imported station geometries remain NULL/UNKNOWN.",
        "quality_warning": "Database quality_flag is UNVERIFIED; original source-reported flags and methods are preserved per row below.",
        "source_row_definition": "Original CSV line number, header is line 1; bulletin locator is retained for each row.",
        "rows": [{"source_row": index, **row} for index, row in enumerate(rows, 2)],
    }
    return rows, sites, digest, metadata


def load_snapshot():
    legacy_rows, sites, legacy_digest, legacy_metadata = load_legacy_snapshot()
    bundle_path = ROOT / "data/research/workspace.json"
    raw = bundle_path.read_bytes()
    manifest = json.loads(bundle_path.with_name("workspace_manifest.json").read_text(encoding="utf-8-sig"))
    digest = hashlib.sha256(raw).hexdigest()
    require(digest == manifest["sha256"], "Workspace manifest hash mismatch")
    bundle = validate_bundle(json.loads(raw))
    sources = {s["source_id"]: s for s in bundle["sources"] if s.get("provider") == "RIA2"}
    issue12 = json.loads((ROOT / "data/metadata/ria2_issue12_transcription.json").read_text(encoding="utf-8"))
    verified_documents = {}
    for code, source in sources.items():
        path = ROOT / issue12["file"] if code == issue12["source_id"] else DIRECTORY / source["file"]
        if path.is_file():
            document = path.read_bytes()
        else:
            # The archived issue-12 PDF may be absent; only its exact hash is accepted.
            try:
                with urllib.request.urlopen(source["url"], timeout=40) as response:
                    document = response.read(20_000_001)
                require(len(document) <= 20_000_000, "Bulletin exceeds verification size limit")
            except (urllib.error.URLError, TimeoutError):
                require(source.get("local_original_status") == "HASH_VERIFIED" and code == issue12["source_id"] and source["sha256"] == issue12["sha256"], "Missing original lacks prior verified provenance")
                document = None
                print("Issue 12 original unavailable for re-verification; using manifest-validated snapshot and prior HASH_VERIFIED provenance.", file=sys.stderr)
        if document is not None:
            require(hashlib.sha256(document).hexdigest() == source["sha256"], "Workspace bulletin hash mismatch")
        verified_documents[code] = source["sha256"]
    records = []
    original_rows = []
    legacy_by_key = {(r["site_code"], r["source_id"]): (n, r) for n, r in enumerate(legacy_rows, 2)}
    for index, row in enumerate(bundle["observations"], 2):
        if not row["site_code"].startswith("RIA2_"):
            continue
        require(row["time_precision"] == "DATE_ONLY" and row["observed_at"] is None, "Workspace temporal precision changed")
        require(row["source_sha256"] == verified_documents[row["source_id"]], "Workspace row provenance mismatch")
        require(math.isclose(row["ec_mS_m"], row["original_value"] * .1), "Workspace unit conversion mismatch")
        records.append({**row, "conductivity_mS_per_m": row["ec_mS_m"], "_source_row": index})
        entry = {"source_row": index, "bundle_observation_index": index - 2, **row}
        legacy = legacy_by_key.get((row["site_code"], row["source_id"]))
        if legacy:
            entry["earlier_csv_provenance"] = {"file": CSV_NAME, "sha256": legacy_digest, "source_row": legacy[0], "row": legacy[1]}
        original_rows.append(entry)
    require(len(records) == 50 and len(sources) == 5, "Expected 50 rows from five RIA2 bulletins")
    require({r["site_code"] for r in records} == set(sites), "Workspace physical station set changed")
    for station in bundle["stations"]:
        if station["site_code"] in sites:
            require(station["geometry"] is None and station["coordinate_crs"] == "NOT_STATED_IN_BULLETIN", "Review station geometry before import")
    metadata = {
        "workspace_manifest": manifest, "time_precision": "DATE_ONLY",
        "timestamp_storage_warning": legacy_metadata["timestamp_storage_warning"],
        "coordinate_warning": legacy_metadata["coordinate_warning"],
        "quality_warning": legacy_metadata["quality_warning"],
        "source_row_definition": "Original workspace observations array index + 2; not a physical JSON line number. Each original bulletin locator is retained per row.",
        "sources": list(sources.values()), "source_document_hashes": verified_documents,
        "document_verification_policy": "Locally available originals are rehashed. Missing issue-12 original is fetched and rehashed when available; otherwise the hash-validated workspace and its prior HASH_VERIFIED provenance are used, without claiming fresh original verification.",
        "issue12_transcription": issue12,
        "supersedes_for_selection_sha256": legacy_digest,
        "predecessor_dataset_code": "RIA2_EC_2025_15_18_" + legacy_digest[:16],
        "correction_note": "Canonical selection is this 50-row workspace snapshot with station-specific sampling dates and issue 12. Earlier 40-row CSV used shared bulletin dates; it remains an immutable provenance artifact, not the current selected observations.",
        "revision_note": "Current validated workspace adds issue 12 and uses corrected station-specific sampling dates. Earlier 40-row recovery dataset remains immutable and must not be blended with this snapshot.",
        "rows": original_rows,
    }
    return records, sites, digest, metadata


def ensure_row(conn, table, key, values, id_column, apply, changes):
    where = sql.SQL(" AND ").join(sql.SQL("{} = %s").format(sql.Identifier(k)) for k in key)
    existing = conn.execute(sql.SQL("SELECT * FROM public.{} WHERE {}").format(sql.Identifier(table), where), list(key.values())).fetchone()
    if existing:
        for name, value in values.items():
            require(existing[name] == value, f"Existing {table} differs in {name}; refusing to overwrite")
        return existing[id_column]
    changes[table] = changes.get(table, 0) + 1
    if not apply:
        return None
    all_values = {**key, **values}
    query = sql.SQL("INSERT INTO public.{} ({}) VALUES ({}) RETURNING {}").format(
        sql.Identifier(table), sql.SQL(",").join(map(sql.Identifier, all_values)),
        sql.SQL(",").join(sql.Placeholder() for _ in all_values), sql.Identifier(id_column),
    )
    params = [Jsonb(v) if isinstance(v, dict) else v for v in all_values.values()]
    return conn.execute(query, params).fetchone()[id_column]


def core_fingerprint(conn):
    return conn.execute("""
        SELECT count(*) AS rows, md5(coalesce(string_agg(row_to_json(o)::text, '' ORDER BY o.ec_observation_id), '')) AS hash
        FROM public.conductivity_observation o JOIN public.data_source s USING(source_id)
        WHERE s.source_code <> %s
    """, (SOURCE_CODE,)).fetchone()


def predecessor_fingerprint(conn, dataset_code):
    return conn.execute("""SELECT count(*) AS rows,
        md5(coalesce(string_agg(row_to_json(o)::text, '' ORDER BY o.ec_observation_id), '')) AS hash
        FROM public.conductivity_observation o JOIN public.source_dataset d USING(dataset_id)
        WHERE d.dataset_code=%s""", (dataset_code,)).fetchone()


def synchronize(apply=False):
    rows, sites, digest, metadata = load_snapshot()
    load_local_env()
    changes = {}
    with read_connection() as conn:
        conn.read_only = not apply
        if apply:
            conn.execute("SELECT pg_advisory_xact_lock(724031650)")
        core_before = core_fingerprint(conn)
        predecessor_before = predecessor_fingerprint(conn, metadata["predecessor_dataset_code"])
        source_id = ensure_row(conn, "data_source", {"source_code": SOURCE_CODE}, {
            "source_name": "RIA2 catfish water-quality monitoring",
            "source_type": "OFFICIAL", "is_demo": False,
            "reference": "RIA2 bulletins 15-18/2025; local hash-verified recovery manifest: data/external/ec_recovery_20261011/ec_recovery_manifest.json",
        }, "source_id", apply, changes)
        dataset_id = ensure_row(conn, "source_dataset", {"sha256": digest}, {
            "dataset_code": "RIA2_WORKSPACE_EC_" + digest[:16], "source_id": source_id,
            "is_demo": False, "dataset_kind": "RAW_EC", "data_product_kind": "IN_SITU_OBSERVATION",
            "source_filename": "data/research/workspace.json", "source_row_count": len(rows), "metadata": metadata,
        }, "dataset_id", apply, changes)
        site_ids = {}
        for code, identity in sites.items():
            site_ids[code] = ensure_row(conn, "measurement_site", {"site_code": code}, {
                "source_id": source_id, "is_demo": False, "country_code": "VN", "external_site_code": code,
                "site_name": identity[0], "geom": None, "location_status": "UNKNOWN",
                "location_reference": "Reported coordinate pair retained in RIA2 source_dataset metadata; source CRS not stated, not independently verified.",
            }, "site_id", apply, changes)
        for row in rows:
            number = row["_source_row"]
            if dataset_id is None:
                changes["conductivity_observation"] = changes.get("conductivity_observation", 0) + 1
                continue
            observed_at = datetime.combine(date.fromisoformat(row["observed_date"]), time(), LOCAL_TZ)
            ensure_row(conn, "conductivity_observation", {"dataset_id": dataset_id, "source_row": number}, {
                "dataset_kind": "RAW_EC", "source_id": source_id, "site_id": site_ids[row["site_code"]],
                "observed_at": observed_at, "conductivity_ms_per_m": float(row["conductivity_mS_per_m"]),
                "unit": "mS/m", "source_label": row["source_id"] + "; DATE_ONLY; midnight+07 storage placeholder, sampling time unknown; " + row["source_locator"],
                "observed_or_estimated": "O", "approval_level": "NOT_INDEPENDENTLY_VERIFIED",
                "grade": row["quality_flag"], "quality_flag": "UNVERIFIED",
            }, "ec_observation_id", apply, changes)
        require(core_fingerprint(conn) == core_before, "Non-RIA2 observations changed")
        require(predecessor_fingerprint(conn, metadata["predecessor_dataset_code"]) == predecessor_before, "Earlier RIA2 artifact changed")
        counts = conn.execute("""SELECT
            (SELECT count(*) FROM public.measurement_site) AS all_sites,
            (SELECT count(*) FROM public.measurement_site s JOIN public.data_source d USING(source_id) WHERE d.source_code=%s) AS ria2_sites,
            (SELECT count(*) FROM public.conductivity_observation WHERE dataset_id=%s) AS snapshot_observations,
            (SELECT count(*) FROM public.measurement_site s JOIN public.data_source d USING(source_id) WHERE d.source_code=%s AND s.geom IS NOT NULL) AS ria2_geometries
        """, (SOURCE_CODE, dataset_id, SOURCE_CODE)).fetchone()
        if apply or dataset_id is not None:
            require(counts["ria2_sites"] == 10 and counts["snapshot_observations"] == len(rows) and counts["ria2_geometries"] == 0, "Post-import counts differ")
        result = {"mode": "applied" if apply else "dry_run", "planned_or_inserted": changes, "database_counts": counts, "non_ria2_observations_unchanged": core_before["rows"], "non_ria2_observations_hash": core_before["hash"], "predecessor_unchanged": predecessor_before, "workspace_sha256": digest}
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Commit validated inserts; default only inspects and reports.")
    args = parser.parse_args()
    print(json.dumps(synchronize(args.apply), indent=2))
