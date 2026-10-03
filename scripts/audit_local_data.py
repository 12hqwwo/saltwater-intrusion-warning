"""Audit supplied data and export station GeoJSON; no database/network access.

Python 3.9+, standard library only. Run from any working directory.
This checks local files, not PostgreSQL contents or scientific data quality.
"""
import argparse
import csv
import hashlib
import json
import math
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "etl"))
import etl_csv

STATIONS = {
    "019803": {"area": "TANCHAU", "label": "Tân Châu", "filename_label": "Tan Chau"},
    "019805": {"area": "MYTHO", "label": "Mỹ Tho", "filename_label": "My Tho"},
}
NS = {"k": "http://www.opengis.net/kml/2.2"}


def file_digest(path):
    content = path.read_bytes()
    return {"sha256": hashlib.sha256(content).hexdigest(), "byte_count": len(content)}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        rows = list(reader)
        if any(None in row or any(v is None for v in row.values()) for row in rows):
            raise ValueError("CSV column count mismatch: " + path.name)
        return reader.fieldnames, rows


def station_feature(path, code):
    """Require one named MRC point; never upgrade REPORTED to VERIFIED."""
    content = path.read_bytes()
    if b"<!DOCTYPE" in content.upper() or b"<!ENTITY" in content.upper():
        raise ValueError("KML DTD/entity declarations are not supported")
    document = ET.fromstring(content)
    placemarks = document.findall(".//k:Placemark", NS)
    if len(placemarks) != 1:
        raise ValueError("Expected exactly one KML Placemark")
    placemark = placemarks[0]
    name = placemark.findtext("k:name", default="", namespaces=NS)
    match = re.search(r"VN_(\d{6})(?:_|$)", name)
    if not match or match.group(1) != code:
        raise ValueError("KML station identity mismatch")
    points = placemark.findall("k:Point", NS)
    if len(points) != 1:
        raise ValueError("Expected exactly one KML Point")
    coordinates = points[0].findtext("k:coordinates", default="", namespaces=NS).split()
    if len(coordinates) != 1:
        raise ValueError("Expected one longitude,latitude[,altitude] tuple")
    values = [float(v) for v in coordinates[0].split(",")]
    if len(values) not in (2, 3) or not all(math.isfinite(v) for v in values):
        raise ValueError("Invalid KML coordinate values")
    lon, lat = values[:2]
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise ValueError("KML coordinates outside longitude/latitude bounds")
    digest = hashlib.sha256(content).hexdigest()
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {
            "site_code": "MRC_VN_" + code, "external_site_code": code,
            "site_name": STATIONS[code]["label"], "area_code": STATIONS[code]["area"],
            "source_code": "MRC_WATER_QUALITY", "location_status": "REPORTED",
            "location_reference": "KML " + path.name + "; sha256=" + digest,
            "source_file": path.name, "source_sha256": digest,
            "unit": "mS/m", "database_state_checked": False,
        },
    }


def compare_monthly_ec(raw_by_area, monthly_rows):
    """Compare values and missingness, including raw months absent from master."""
    expected = defaultdict(list)
    for area, records in raw_by_area.items():
        for row in records:
            expected[(area, row["observed_at"][:7] + "-01")].append(row["conductivity_ms_per_m"])
    actual = {(r["area_code"], r["month_start"]): r["conductivity_ms_per_m"] for r in monthly_rows}
    differences = []
    for key in sorted(set(expected) | set(actual)):
        values = expected.get(key, [])
        mean = math.fsum(values) / len(values) if values else None
        value = actual.get(key)
        if key not in actual or (mean is None) != (value is None) or (
            mean is not None and value is not None
            and not math.isclose(mean, value, rel_tol=1e-9, abs_tol=1e-9)
        ):
            differences.append({"area_code": key[0], "month_start": key[1],
                                "raw_monthly_mean": mean, "master_ec": value})
    return differences


def forecast_summary(directory, monthly_rows):
    """Recompute metrics from exports only; does not rerun or validate model fit."""
    _, predictions = read_csv(directory / "predictions.csv")
    _, saved_metrics = read_csv(directory / "metrics.csv")
    monthly = {r["month_start"]: r["conductivity_ms_per_m"]
               for r in monthly_rows if r["area_code"] == "MYTHO"}
    groups, seen = defaultdict(list), set()
    for row in predictions:
        if row["station"] not in ("Mỹ Tho", "MyTho", "MYTHO"):
            raise ValueError("Unexpected station in forecast export")
        target = date.fromisoformat(row["target_month"][:10]).isoformat()
        key = row["model"], target
        if key in seen:
            raise ValueError("Duplicate model/target_month in predictions")
        seen.add(key)
        actual = float(row["actual"]) if row["actual"] else None
        expected = monthly.get(target)
        if (actual is None) != (expected is None) or (actual is not None and (
            not math.isfinite(actual) or not math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9)
        )):
            raise ValueError("Forecast actual does not match supplied master: " + target)
        groups[row["model"]]  # Keep models even when every prediction is skipped.
        if row["status"] == "SUCCESS":
            prediction = float(row["predicted"])
            if not math.isfinite(prediction):
                raise ValueError("Non-finite successful prediction")
            if actual is not None:
                groups[row["model"]].append((target, actual, prediction))
    keys = {model: {r[0] for r in rows} for model, rows in groups.items()}
    common = set.intersection(*keys.values()) if keys else set()
    recalculated = []
    matches = Counter(r['model'] for r in saved_metrics) == Counter(
        model for model, rows in groups.items() if rows
    )
    for model, rows in sorted(groups.items()):
        if not rows:
            recalculated.append({"model": model, "eval_samples": 0, "mae_mS_m": None, "rmse_mS_m": None})
            continue
        mae = math.fsum(abs(y - p) for _, y, p in rows) / len(rows)
        rmse = math.sqrt(math.fsum((y - p) ** 2 for _, y, p in rows) / len(rows))
        recalculated.append({"model": model, "eval_samples": len(rows), "mae_mS_m": mae, "rmse_mS_m": rmse})
        saved = [r for r in saved_metrics if r["model"] == model]
        matches = matches and len(saved) == 1 and int(saved[0]["eval_samples"]) == len(rows)
        if saved:
            matches = matches and math.isclose(float(saved[0]["mae_mS_m"]), mae, rel_tol=1e-9, abs_tol=1e-9)
            matches = matches and math.isclose(float(saved[0]["rmse_mS_m"]), rmse, rel_tol=1e-9, abs_tol=1e-9)
    return {"metrics_recalculated": recalculated, "saved_metrics_match": matches,
            "common_target_months": sorted(common), "same_scoring_months": bool(common) and all(k == common for k in keys.values()),
            "model_fit_rerun": False, "availability_and_leakage_verified": False}


def boundary_summary(path):
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    if document.get("type") != "FeatureCollection":
        raise ValueError("Expected boundary FeatureCollection")
    features = document.get("features", [])
    points = []
    def visit(value):
        if not isinstance(value, list) or not value:
            raise ValueError("Empty/invalid boundary coordinate array")
        if isinstance(value[0], (int, float)):
            if len(value) < 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in value):
                raise ValueError("Invalid boundary coordinate values")
            x, y = value[:2]
            if not (-180 <= x <= 180 and -90 <= y <= 90):
                raise ValueError("Boundary coordinates outside longitude/latitude bounds")
            points.append((x, y))
        else:
            for item in value:
                visit(item)
    for feature in features:
        geometry = feature.get("geometry") or {}
        if geometry.get("type") not in ("Polygon", "MultiPolygon"):
            raise ValueError("Expected Polygon/MultiPolygon boundary")
        visit(geometry["coordinates"])
    if not points:
        raise ValueError("No boundary positions")
    return {"file": path.name, **file_digest(path), "feature_count": len(features),
            "geometry_types": sorted({f["geometry"]["type"] for f in features}),
            "bbox": [min(p[0] for p in points), min(p[1] for p in points),
                     max(p[0] for p in points), max(p[1] for p in points)],
            "declared_crs": document.get("crs"),
            "coordinate_range_check": "PASS", "topology_check": "NOT_RUN",
            "source_and_effective_dates": "NEEDS_DOCUMENTED_PROVENANCE"}


def audit_project(root):
    report = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "LOCAL_FILES_ONLY", "database_checked": False,
              "checks": [], "inputs": {}, "raw_ec": [], "monthly": [],
              "boundaries": [], "stations": [], "forecast_exports": None}
    def check(status, name, detail):
        report["checks"].append({"status": status, "check": name, "detail": detail})
    def capture(path):
        report["inputs"][path.relative_to(root).as_posix()] = file_digest(path)
    raw_by_area, manifest_files = {}, {}
    for code, meta in STATIONS.items():
        base = "Conductivity.Water Quality@VN_" + code + "_[" + meta["filename_label"] + "]"
        path = root / "data/raw/mrc_conductivity" / (base + ".csv")
        try:
            capture(path)
            rows, rejects, total = etl_csv.validate(path.read_bytes(), "raw", code)
            if rejects or not rows:
                raise ValueError("Rejected rows: " + str(len(rejects)) + "; first reasons: " + str(rejects[:2]))
            raw_by_area[meta["area"]] = rows
            report["raw_ec"].append({"area_code": meta["area"], "site_code": "MRC_VN_" + code,
                "rows": total, "first_observation": min(r["observed_at"] for r in rows),
                "last_observation": max(r["observed_at"] for r in rows), "unit": "mS/m",
                "observed_or_estimated": dict(Counter(r["observed_or_estimated"] for r in rows)),
                "approval_level": dict(Counter(r["approval_level"] for r in rows)),
                "grade": dict(Counter(r["grade"] for r in rows))})
            check("PASS", "raw_" + code, str(total) + " rows passed existing ETL validation")
            manifest_files["mrc_" + ("tanchau" if code == "019803" else "mytho") + ".csv"] = path
        except (OSError, ValueError, csv.Error, UnicodeError) as exc:
            check("FAIL", "raw_" + code, str(exc))
        try:
            kml = root / "data/raw/spatial" / (base + "__station-location.kml")
            capture(kml)
            feature = station_feature(kml, code)
            original = root / "data/raw/mrc_conductivity" / kml.name
            if original.read_bytes() != kml.read_bytes():
                raise ValueError("The two copies of the station KML differ")
            report["stations"].append(feature)
            check("PASS", "station_kml_" + code, "Named point parsed; duplicate KML copies match; REPORTED")
            manifest_files[("tanchau" if code == "019803" else "mytho") + "_location.kml"] = kml
        except (OSError, ValueError, ET.ParseError, UnicodeError) as exc:
            check("FAIL", "station_kml_" + code, str(exc))
    monthly_rows = []
    try:
        path = root / "data/processed/master_timeseries.csv"
        capture(path)
        manifest_files["master_timeseries.csv"] = path
        monthly_rows, rejects, total = etl_csv.validate(path.read_bytes(), "master")
        if rejects or not monthly_rows:
            raise ValueError("Rejected master rows: " + str(len(rejects)) + "; first reasons: " + str(rejects[:2]))
        for area in sorted({r["area_code"] for r in monthly_rows}):
            rows = [r for r in monthly_rows if r["area_code"] == area]
            months = sorted(r["month_start"] for r in rows)
            first, last = date.fromisoformat(months[0]), date.fromisoformat(months[-1])
            expected_count = (last.year - first.year) * 12 + last.month - first.month + 1
            coverage = {}
            for field in etl_csv.FEATURES:
                available = [r["month_start"] for r in rows if r[field] is not None]
                coverage[field] = {"non_null_months": len(available),
                                   "first_month": min(available) if available else None,
                                   "last_month": max(available) if available else None}
            report["monthly"].append({"area_code": area, "rows": len(rows), "first_month": months[0],
                                      "last_month": months[-1], "coverage": coverage})
            check("PASS" if expected_count == len(rows) else "FAIL", "calendar_" + area,
                  str(len(rows)) + "/" + str(expected_count) + " calendar months present")
        check("PASS", "master_validation", str(total) + " rows passed existing ETL validation")
        if len(raw_by_area) != len(STATIONS):
            check("FAIL", "raw_master_ec", "Comparison incomplete: raw input validation failed")
        else:
            differences = compare_monthly_ec(raw_by_area, monthly_rows)
            report["ec_mismatches"] = differences
            check("FAIL" if differences else "PASS", "raw_master_ec",
                  str(len(differences)) + " month/value/missingness differences")
    except (OSError, ValueError, csv.Error, UnicodeError) as exc:
        check("FAIL", "master_validation", str(exc))
        monthly_rows = []
    try:
        header, manifest = read_csv(root / "docs/etl/source_manifest.csv")
        if header != ["file", "original_filename", "sha256", "byte_count"]:
            raise ValueError("Source manifest header is not a four-column CSV")
        if Counter(r["file"] for r in manifest) != Counter(manifest_files.keys()):
            raise ValueError("Source manifest entries differ from the five expected inputs")
        for row in manifest:
            path = manifest_files[row["file"]]
            digest = file_digest(path)
            if digest["sha256"] != row["sha256"] or digest["byte_count"] != int(row["byte_count"]) or path.name != row["original_filename"]:
                raise ValueError("Source manifest mismatch: " + row["file"])
        check("PASS", "source_manifest", "All five original input hashes and sizes match")
    except (OSError, ValueError, KeyError, csv.Error, UnicodeError) as exc:
        check("FAIL", "source_manifest", str(exc))
    paths = sorted((root / "data/biengioi").glob("*.geojson"))
    for path in paths:
        try:
            capture(path)
            report["boundaries"].append(boundary_summary(path))
            check("PASS", "boundary_structure_" + path.name, "Polygon type and numeric coordinate bounds checked only")
        except (OSError, ValueError, KeyError, TypeError, UnicodeError) as exc:
            check("FAIL", "boundary_structure_" + path.name, str(exc))
    check("WARN", "boundary_provenance", "Source, effective dates, topology and database import need separate verification")
    try:
        _, gates = read_csv(root / "data/irrigation_gates_template.csv")
        report["gate_template_rows"] = len(gates)
        check("WARN", "gate_catalog", "Template rows: " + str(len(gates)) + "; this is not the database gate count or evidence of real gates")
    except (OSError, ValueError, csv.Error, UnicodeError) as exc:
        check("FAIL", "gate_template", str(exc))
    if monthly_rows:
        try:
            for filename in ["predictions.csv", "metrics.csv", "split_manifest.csv"]:
                capture(root / "runs/forecast_exp" / filename)
            summary = forecast_summary(root / "runs/forecast_exp", monthly_rows)
            report["forecast_exports"] = summary
            check("PASS" if summary["saved_metrics_match"] else "FAIL", "exported_metrics",
                  "Recalculated from saved predictions; model fitting not rerun")
            check("PASS" if summary["same_scoring_months"] else "WARN", "forecast_cohort",
                  str(len(summary["common_target_months"])) + " target months shared by all models")
        except (OSError, ValueError, KeyError, csv.Error, UnicodeError) as exc:
            check("FAIL", "forecast_exports", str(exc))
    check("WARN", "forecast_method", "Forecast issue time, data availability and validation protocol are not certified by this audit")
    check("WARN", "database_state", "No database connection made; existing database contents remain unknown to this run")
    report["status"] = "FAILED" if any(c["status"] == "FAIL" for c in report["checks"]) else "PASS_WITH_LIMITATIONS"
    return report


def markdown_report(report):
    lines = ["# Kiểm tra dữ liệu cục bộ WebGIS", "", "Thời điểm UTC: " + report["generated_at_utc"],
             "", "Kết quả: **" + report["status"] + "**.", "",
             "Phạm vi: file trong dự án. Chưa kết nối PostgreSQL; không xác nhận chất lượng chuyên môn hoặc khả năng vận hành.",
             "", "## EC gốc", "", "| Khu vực | Số dòng | Quan trắc đầu | Quan trắc cuối | Đơn vị |", "|---|---:|---|---|---|"]
    for row in report["raw_ec"]:
        lines.append(f"| {row['area_code']} | {row['rows']} | {row['first_observation']} | {row['last_observation']} | {row['unit']} |")
    lines += ["", "## Dữ liệu tháng", "", "| Khu vực | Số tháng lịch | Tháng có EC | Tháng có DAHITI | Tháng có GloFAS |", "|---|---:|---:|---:|---:|"]
    for row in report["monthly"]:
        c = row["coverage"]
        lines.append(f"| {row['area_code']} | {row['rows']} | {c['conductivity_ms_per_m']['non_null_months']} | {c['water_level_m']['non_null_months']} | {c['glofas_discharge_m3s']['non_null_months']} |")
    lines += ["", "Lịch tháng kéo dài không đồng nghĩa có quan trắc EC ở tất cả các tháng. Đối chiếu EC chỉ kiểm tra phép tổng hợp từ file gốc, không nâng cờ chất lượng.",
              "", "## Tọa độ trạm từ KML", "", "| Mã trạm | Kinh độ | Vĩ độ | Trạng thái |", "|---|---:|---:|---|"]
    for feature in report["stations"]:
        p, xy = feature["properties"], feature["geometry"]["coordinates"]
        lines.append(f"| {p['site_code']} | {xy[0]} | {xy[1]} | REPORTED |")
    lines += ["", "GeoJSON được xuất từ KML đính kèm, giữ mã trạm và SHA-256. Đây không phải xác nhận vị trí đã nạp vào database.",
              "", "## Kiểm tra", "", "| Trạng thái | Nội dung | Kết quả |", "|---|---|---|"]
    for c in report["checks"]:
        detail = c["detail"].replace("|", "/").replace("\n", " ")
        lines.append(f"| {c['status']} | {c['check']} | {detail} |")
    if report["forecast_exports"]:
        summary = report["forecast_exports"]
        lines += ["", "## Tính lại kết quả dự báo đã lưu", "", "| Mô hình | Số tháng chấm | MAE (mS/m) | RMSE (mS/m) |", "|---|---:|---:|---:|"]
        for r in summary["metrics_recalculated"]:
            lines.append(f"| {r['model']} | {r['eval_samples']} | {r['mae_mS_m']} | {r['rmse_mS_m']} |")
        lines += ["", "Chỉ tính lại sai số từ predictions.csv; chưa huấn luyện lại hoặc xác minh thời điểm phát hành dự báo."]
    lines += ["", "Chi tiết, SHA-256 và độ phủ từng biến nằm trong audit_report.json. Các giới hạn phải được xử lý trước khi công bố chức năng tương ứng.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Project directory")
    parser.add_argument("--out", type=Path, help="New output directory; must not already exist")
    args = parser.parse_args()
    root = args.root.resolve()
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    output = args.out.resolve() if args.out else root / "runs/local_audit" / name
    if output.exists():
        parser.error("Output directory already exists; choose a new one")
    report = audit_project(root)
    output.mkdir(parents=True, exist_ok=False)
    (output / "audit_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (output / "audit_report.md").write_text(markdown_report(report), encoding="utf-8")
    # Publish the station layer only if both KMLs passed identity/range checks.
    if len(report["stations"]) == len(STATIONS):
        collection = {"type": "FeatureCollection", "features": report["stations"]}
        (output / "stations_from_kml.geojson").write_text(json.dumps(collection, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(output),
                      "failures": sum(c["status"] == "FAIL" for c in report["checks"]),
                      "warnings": sum(c["status"] == "WARN" for c in report["checks"])}, ensure_ascii=False, indent=2))
    return 1 if report["status"] == "FAILED" else 0


if __name__ == "__main__":
    sys.exit(main())
