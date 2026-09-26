#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Migration 03 - Đồng Tháp mới: 1 ranh giới tỉnh + 102 xã/phường.

Cách hoạt động:
  Python chạy bằng tài khoản Windows của người dùng (không qua PostgreSQL Service)
  -> tải GeoJSON từ GitHub raw
  -> validate đủ 103 file
  -> sinh load.sql tự chứa geometry
  -> tùy chọn gọi psql để nạp vào dongthap_gis.

Không cần thư viện Python ngoài standard library.

Mặc định là PREVIEW: SQL kết thúc bằng ROLLBACK.
Chỉ dùng --commit sau khi preview thành công.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request

PROVINCE_CODE = "82"
PROVINCE_FILENAME = "82_dong_thap.geojson"
BASE_RAW = (
    "https://raw.githubusercontent.com/"
    "thanglequoc/vietnamese-provinces-database/"
    "master/json/geojson/82_dong_thap"
)

WARD_STEMS = ['28249_dao_thanh', '28261_my_tho', '28270_thoi_son', '28273_my_phong', '28285_trung_an', '28297_long_thuan', '28306_go_cong', '28315_binh_xuan', '28321_tan_phuoc_1', '28327_tan_phuoc_2', '28336_hung_thanh', '28345_tan_phuoc_3', '28360_cai_be', '28366_hau_my', '28378_my_thien', '28393_hoi_cu', '28405_my_duc_tay', '28414_my_loi', '28426_thanh_hung', '28429_an_huu', '28435_my_phuoc_tay', '28436_thanh_hoa', '28439_cai_lay', '28444_thanh_phu', '28456_my_thanh', '28468_tan_phu', '28471_binh_phu', '28477_nhi_quy', '28501_hiep_duc', '28504_long_tien', '28516_ngu_hiep', '28519_chau_thanh', '28525_tan_huong', '28537_long_hung', '28543_long_dinh', '28564_binh_trung', '28576_vinh_kim', '28582_kim_son', '28594_cho_gao', '28603_my_tinh_an', '28615_luong_hoa_lac', '28627_tan_thuan_binh', '28633_an_thanh_thuy', '28648_binh_ninh', '28651_vinh_binh', '28660_dong_son', '28663_phu_thanh', '28678_vinh_huu', '28687_long_binh', '28693_tan_thoi', '28696_tan_phu_dong', '28702_tan_hoa', '28720_gia_thuan', '28723_tan_dong', '28729_son_qui', '28738_tan_dien', '28747_go_cong_dong', '29869_cao_lanh', '29884_my_ngai', '29888_my_tra', '29905_sa_dec', '29926_tan_hong', '29929_tan_ho_co', '29938_tan_thanh', '29944_an_phuoc', '29954_an_binh', '29955_hong_ngu', '29971_thuong_phuoc', '29978_thuong_lac', '29983_long_khanh', '29992_long_phu_thuan', '30001_tram_chim', '30010_tam_nong', '30019_an_hoa', '30025_phu_cuong', '30028_an_long', '30034_phu_tho', '30037_thap_muoi', '30043_phuong_thinh', '30046_truong_xuan', '30055_my_qui', '30061_doc_binh_kieu', '30073_thanh_my', '30076_my_tho', '30085_ba_sao', '30088_phong_my', '30112_my_hiep', '30118_binh_hang_trung', '30130_thanh_binh', '30154_tan_long', '30157_tan_thanh', '30163_binh_thanh', '30169_lap_vo', '30178_my_an_hung', '30184_tan_khanh_trung', '30208_hoa_long', '30214_tan_duong', '30226_lai_vung', '30235_phong_hoa', '30244_phu_huu', '30253_tan_nhuan_dong', '30259_tan_phu_trung']

SOURCE_CODE = "TLQ_VNM_ADMIN_GIS_2026"
VALID_FROM = "2025-07-01"


def parse_args():
    p = argparse.ArgumentParser(
        description="Nạp ranh giới Đồng Tháp mới: 1 tỉnh + 102 xã/phường."
    )
    p.add_argument("--db", default="dongthap_gis")
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", default="5432")
    p.add_argument("--user", default="postgres")
    p.add_argument(
        "--psql",
        default=r"C:\Program Files\PostgreSQL\17\bin\psql.exe",
        help="Đường dẫn psql.exe",
    )
    p.add_argument(
        "--out",
        default=r"D:\TLCN_ADMIN_RUNS",
        help="Thư mục lưu run, GeoJSON và load.sql",
    )
    p.add_argument(
        "--load",
        action="store_true",
        help="Gọi psql sau khi tải + validate + sinh SQL.",
    )
    p.add_argument(
        "--commit",
        action="store_true",
        help="Ghi thật. Nếu không có flag này, SQL dùng ROLLBACK.",
    )
    return p.parse_args()


def fetch(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TLCN-DongThap-GIS/1.0",
            "Accept": "application/geo+json,application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}: {url}")
        return resp.read()


def load_feature(data: bytes, expected_code: str, label: str):
    try:
        obj = json.loads(data.decode("utf-8-sig"))
    except Exception as e:
        raise RuntimeError(f"{label}: JSON không đọc được: {e}") from e

    if obj.get("type") != "FeatureCollection":
        raise RuntimeError(f"{label}: không phải FeatureCollection.")

    features = obj.get("features")
    if not isinstance(features, list) or len(features) != 1:
        raise RuntimeError(
            f"{label}: cần đúng 1 Feature, hiện có "
            f"{len(features) if isinstance(features, list) else 'không hợp lệ'}."
        )

    f = features[0]
    geom = f.get("geometry")
    if not isinstance(geom, dict) or geom.get("type") not in ("Polygon", "MultiPolygon"):
        raise RuntimeError(f"{label}: geometry không phải Polygon/MultiPolygon.")

    props = f.get("properties") or {}
    code = str(props.get("code") or f.get("id") or "")
    if code != expected_code:
        raise RuntimeError(
            f"{label}: mã trong GeoJSON = {code!r}, kỳ vọng = {expected_code!r}."
        )

    full_name = props.get("fullName") or props.get("name")
    if not full_name:
        raise RuntimeError(f"{label}: thiếu fullName/name.")

    return str(full_name), geom


def sql_text(value: str) -> str:
    # Use only for strings guaranteed to be ASCII.
    return "'" + value.replace("'", "''") + "'"


def sql_utf8_expr(value: str) -> str:
    # Return an ASCII-only SQL expression that reconstructs UTF-8 text in PostgreSQL.
    # This makes load.sql independent of the Windows psql input encoding.
    hex_value = value.encode("utf-8").hex()
    return "convert_from(decode('" + hex_value + "','hex'),'UTF8')"


def geom_expr(geom: dict) -> str:
    geo = json.dumps(geom, ensure_ascii=True, separators=(",", ":"))
    # geometry JSON chỉ cần escape dấu nháy đơn để thành SQL literal an toàn.
    return (
        "ST_Multi(ST_CollectionExtract(ST_MakeValid("
        "ST_SetSRID(ST_GeomFromGeoJSON("
        + sql_text(geo)
        + "),4326)),3))::geometry(MultiPolygon,4326)"
    )


def boundary_upsert(code: str, name: str, level: str, geom: dict) -> str:
    return f"""
INSERT INTO public.admin_boundary
  (boundary_code, boundary_name, admin_level,
   valid_from, valid_to, source_id, is_demo, geom)
SELECT
  {sql_text('TLQ_' + code)},
  {sql_utf8_expr(name)},
  {sql_text(level)},
  DATE {sql_text(VALID_FROM)},
  NULL,
  s.source_id,
  false,
  {geom_expr(geom)}
FROM public.data_source s
WHERE s.source_code = {sql_text(SOURCE_CODE)}
ON CONFLICT (boundary_code, valid_from, is_demo) DO UPDATE
SET boundary_name = EXCLUDED.boundary_name,
    admin_level   = EXCLUDED.admin_level,
    valid_to      = EXCLUDED.valid_to,
    source_id     = EXCLUDED.source_id,
    geom          = EXCLUDED.geom;
""".strip()


def make_sql(records, commit: bool) -> str:
    pieces = []
    pieces.append(r"""-- ============================================================================
-- Migration 03 GENERATED V5 ASCII-SQL
-- Dong Thap moi: 1 province + 102 commune/ward boundaries
-- Python downloads and embeds geometry directly into this SQL file.
-- No COPY FROM PROGRAM. PostgreSQL Service does not need Internet access.
-- ============================================================================

\set ON_ERROR_STOP on
\encoding UTF8

BEGIN;

SET LOCAL search_path = public, pg_catalog;
SET LOCAL TIME ZONE 'Asia/Ho_Chi_Minh';
SET LOCAL lock_timeout = '30s';
SET LOCAL statement_timeout = '15min';

DO $guard$
BEGIN
  IF current_database() <> 'dongthap_gis' THEN
    RAISE EXCEPTION 'Can database dongthap_gis. Dang o: %', current_database();
  END IF;
  IF to_regclass('public.admin_boundary') IS NULL THEN
    RAISE EXCEPTION 'Chua co public.admin_boundary; chay 01_core_schema_if_new.sql truoc.';
  END IF;
  IF to_regclass('public.data_source') IS NULL THEN
    RAISE EXCEPTION 'Chua co public.data_source; chay 01_core_schema_if_new.sql truoc.';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname='postgis') THEN
    RAISE EXCEPTION 'PostGIS chua duoc bat.';
  END IF;
END
$guard$;

INSERT INTO public.data_source
  (source_code, source_name, source_type, reference, is_demo)
VALUES (
  'TLQ_VNM_ADMIN_GIS_2026',
  'Vietnamese Provinces Database - GIS administrative boundaries',
  'RESEARCH',
  'https://github.com/thanglequoc/vietnamese-provinces-database ; '
  || 'Dong Thap code 82; GeoJSON EPSG:4326',
  false
)
ON CONFLICT (source_code) DO UPDATE
SET source_name = EXCLUDED.source_name,
    source_type = EXCLUDED.source_type,
    reference   = EXCLUDED.reference,
    is_demo     = EXCLUDED.is_demo;

DELETE FROM public.admin_boundary
WHERE boundary_code LIKE 'GADM41%';
""")

    for rec in records:
        pieces.append(
            boundary_upsert(
                rec["code"], rec["name"], rec["level"], rec["geometry"]
            )
        )

    pieces.append(r"""
DO $verify$
DECLARE
  n_province integer;
  n_commune integer;
  invalid_count integer;
  wrong_srid_count integer;
BEGIN
  SELECT count(*) INTO n_province
  FROM public.admin_boundary
  WHERE boundary_code='TLQ_82'
    AND valid_from=DATE '2025-07-01'
    AND is_demo=false
    AND admin_level='PROVINCE';

  SELECT count(*) INTO n_commune
  FROM public.admin_boundary
  WHERE boundary_code LIKE 'TLQ\_%' ESCAPE '\'
    AND boundary_code <> 'TLQ_82'
    AND valid_from=DATE '2025-07-01'
    AND is_demo=false
    AND admin_level='COMMUNE';

  SELECT count(*) INTO invalid_count
  FROM public.admin_boundary
  WHERE boundary_code LIKE 'TLQ\_%' ESCAPE '\'
    AND valid_from=DATE '2025-07-01'
    AND is_demo=false
    AND NOT ST_IsValid(geom);

  SELECT count(*) INTO wrong_srid_count
  FROM public.admin_boundary
  WHERE boundary_code LIKE 'TLQ\_%' ESCAPE '\'
    AND valid_from=DATE '2025-07-01'
    AND is_demo=false
    AND ST_SRID(geom) <> 4326;

  RAISE NOTICE
    'FINAL: PROVINCE=%, COMMUNE=%, invalid_geometry=%, wrong_srid=%',
    n_province, n_commune, invalid_count, wrong_srid_count;

  IF n_province <> 1 OR n_commune <> 102
     OR invalid_count <> 0 OR wrong_srid_count <> 0 THEN
    RAISE EXCEPTION
      'Kiem tra cuoi khong dat: province=%, commune=%, invalid=%, wrong_srid=%',
      n_province, n_commune, invalid_count, wrong_srid_count;
  END IF;
END
$verify$;

SELECT
  admin_level,
  count(*) AS so_luong,
  count(*) FILTER (WHERE ST_IsValid(geom)) AS geometry_hop_le,
  count(*) FILTER (WHERE ST_SRID(geom)=4326) AS srid_4326
FROM public.admin_boundary
WHERE boundary_code LIKE 'TLQ\_%' ESCAPE '\'
  AND valid_from=DATE '2025-07-01'
  AND is_demo=false
GROUP BY admin_level
ORDER BY admin_level;

SELECT
  boundary_code,
  boundary_name,
  admin_level,
  ST_GeometryType(geom) AS geom_type,
  ST_SRID(geom) AS srid,
  ST_IsValid(geom) AS is_valid,
  ROUND((ST_Area(geom::geography)/1e6)::numeric,2) AS area_km2
FROM public.admin_boundary
WHERE boundary_code LIKE 'TLQ\_%' ESCAPE '\'
  AND valid_from=DATE '2025-07-01'
  AND is_demo=false
ORDER BY admin_level, boundary_code;
""")

    pieces.append("COMMIT;\n" if commit else "ROLLBACK;\n")
    return "\n\n".join(pieces)


def main():
    args = parse_args()

    if args.db != "dongthap_gis":
        raise SystemExit(
            f"SAFETY: script này chỉ cho phép --db dongthap_gis, hiện là {args.db!r}"
        )

    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(args.out) / f"{stamp}_admin_boundary_03"
    raw_dir = run_dir / "geojson"
    ward_dir = raw_dir / "wards"
    ward_dir.mkdir(parents=True, exist_ok=True)

    records = []
    manifest = []

    print("[1/4] Tải ranh giới tỉnh Đồng Tháp...")
    province_url = f"{BASE_RAW}/{PROVINCE_FILENAME}"
    pdata = fetch(province_url)
    (raw_dir / PROVINCE_FILENAME).write_bytes(pdata)
    pname, pgeom = load_feature(pdata, "82", PROVINCE_FILENAME)
    records.append(
        {"code": "82", "name": pname, "level": "PROVINCE", "geometry": pgeom}
    )
    manifest.append(
        {
            "code": "82",
            "file": PROVINCE_FILENAME,
            "url": province_url,
            "sha256": hashlib.sha256(pdata).hexdigest(),
            "bytes": len(pdata),
        }
    )

    print("[2/4] Tải 102 ranh giới xã/phường...")
    failures = []
    for i, stem in enumerate(WARD_STEMS, start=1):
        filename = stem + ".geojson"
        code = stem[:5]
        url = f"{BASE_RAW}/wards/{filename}"
        try:
            data = fetch(url)
            (ward_dir / filename).write_bytes(data)
            name, geom = load_feature(data, code, filename)
            records.append(
                {
                    "code": code,
                    "name": name,
                    "level": "COMMUNE",
                    "geometry": geom,
                }
            )
            manifest.append(
                {
                    "code": code,
                    "file": filename,
                    "url": url,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "bytes": len(data),
                }
            )
        except Exception as e:
            failures.append({"file": filename, "error": str(e)})
            print(f"  [LỖI] {filename}: {e}", file=sys.stderr)

        if i % 10 == 0 or i == 102:
            print(f"  {i}/102")

    province_n = sum(1 for r in records if r["level"] == "PROVINCE")
    commune_n = sum(1 for r in records if r["level"] == "COMMUNE")
    distinct_commune = len({r["code"] for r in records if r["level"] == "COMMUNE"})

    report = {
        "run_at_utc": stamp,
        "database": args.db,
        "source": BASE_RAW,
        "province_count": province_n,
        "commune_count": commune_n,
        "distinct_commune_codes": distinct_commune,
        "expected_total": 103,
        "downloaded_total": len(records),
        "failures": failures,
        "mode": "COMMIT" if args.commit else "PREVIEW_ROLLBACK",
    }

    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (run_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        f"[3/4] Kiểm tra: tỉnh={province_n}, xã/phường={commune_n}, "
        f"mã xã/phường khác nhau={distinct_commune}"
    )

    if failures or province_n != 1 or commune_n != 102 or distinct_commune != 102:
        raise SystemExit(
            "DỪNG: chưa tải/validate đủ 1 tỉnh + 102 xã/phường. "
            f"Xem {run_dir / 'report.json'}"
        )

    load_sql = run_dir / "load.sql"
    load_sql.write_text(make_sql(records, args.commit), encoding="ascii")
    print(f"[4/4] Đã sinh SQL: {load_sql}")

    if not args.load:
        print("Chưa nạp DB vì chưa có --load.")
        print("PREVIEW mặc định: load.sql kết thúc bằng ROLLBACK.")
        return

    psql = Path(args.psql)
    if not psql.exists():
        raise SystemExit(f"Không tìm thấy psql.exe: {psql}")

    cmd = [
        str(psql),
        "-X",
        "-v",
        "ON_ERROR_STOP=1",
        "-h",
        args.host,
        "-p",
        str(args.port),
        "-U",
        args.user,
        "-d",
        args.db,
        "-f",
        str(load_sql),
    ]

    print("V5 ASCII-SQL: đang gọi psql (không phụ thuộc WIN1252/UTF8 của file SQL)...")
    env = os.environ.copy()
    env["PGCLIENTENCODING"] = "UTF8"
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        raise SystemExit(f"psql thất bại, exit code={result.returncode}")

    if args.commit:
        print("THÀNH CÔNG: đã COMMIT 1 tỉnh + 102 xã/phường.")
    else:
        print(
            "THÀNH CÔNG PREVIEW: SQL chạy hợp lệ nhưng đã ROLLBACK. "
            "Nếu output đúng, chạy lại với --commit."
        )


if __name__ == "__main__":
    main()
