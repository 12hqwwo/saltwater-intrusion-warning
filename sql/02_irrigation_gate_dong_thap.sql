-- =============================================================================
-- Migration 02: Nạp danh sách 15 cống thủy lợi vào public.irrigation_gate
-- Nguồn: sluice_gates_dong_thap_new.geojson + README_sluice_gates.md
-- CRS:   EPSG:4326 / WGS84
-- Ngày:  2026-09-26
--
-- Phạm vi:
--   - DTG001–DTG012 : 12 cống có tọa độ (3 điểm direct_published, 9 derived/medium)
--   - DTG013–DTG015 : 3 cống Pending chưa xác định tọa độ; is_active=false,
--                     geom đặt tại centroid vùng nghiên cứu (10.36°N 106.37°E)
--                     chỉ để định danh, không dùng trong phân tích không gian.
--
-- Cách chạy (mặc định ROLLBACK — xem trước kết quả):
--   Mở Query Tool của dongthap_gis → chạy toàn bộ file (F5).
--   Khi đã xác nhận đúng, đổi dòng CUỐI thành COMMIT rồi chạy lại TOÀN BỘ.
-- =============================================================================

BEGIN;
SET LOCAL search_path = public, pg_catalog;
SET LOCAL TIME ZONE 'Asia/Ho_Chi_Minh';
SET LOCAL lock_timeout = '10s';

-- Guard: đúng database
DO $guard$ BEGIN
  IF current_database() <> 'dongthap_gis' THEN
    RAISE EXCEPTION 'Can database dongthap_gis. Dang o: %', current_database();
  END IF;
END $guard$;

-- Guard: bảng irrigation_gate phải tồn tại
DO $guard$ BEGIN
  IF to_regclass('public.irrigation_gate') IS NULL THEN
    RAISE EXCEPTION 'Chua co bang irrigation_gate; chay 01_core_schema_if_new.sql truoc.';
  END IF;
END $guard$;

-- Guard: bảng data_source phải có source cho cống
-- Tạo source nếu chưa có
INSERT INTO public.data_source (source_code, source_name, source_type, reference, is_demo)
VALUES (
  'SLICEGATE_DONGTHAPMOI_2026',
  'Danh muc cong thuy loi Dong Thap moi – TLCN 2026',
  'RESEARCH',
  'GeoJSON tong hop tu QD 04/2019/QD-UBND TG, QD 12/2023/QD-UBND TG, TT 18/2017/TT-BTNMT; phuong phap suy ra ghi trong README_sluice_gates.md',
  false
)
ON CONFLICT (source_code) DO NOTHING;

-- Guard: source phải tồn tại và không phải demo
DO $guard$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.data_source
    WHERE source_code = 'SLICEGATE_DONGTHAPMOI_2026' AND is_demo = false
  ) THEN
    RAISE EXCEPTION 'Khong tim thay source SLICEGATE_DONGTHAPMOI_2026 hop le.';
  END IF;
END $guard$;

-- Guard: không import nếu đã có gate_code bị trùng
DO $guard$ BEGIN
  IF EXISTS (
    SELECT 1 FROM public.irrigation_gate
    WHERE gate_code IN (
      'DTG001','DTG002','DTG003','DTG004','DTG005','DTG006','DTG007',
      'DTG008','DTG009','DTG010','DTG011','DTG012',
      'DTG013','DTG014','DTG015'
    )
  ) THEN
    RAISE EXCEPTION 'Da co gate_code trung; kiem tra lai truoc khi chay.';
  END IF;
END $guard$;

-- ─────────────────────────────────────────────────────────────────────────────
-- INSERT 12 CỐNG CÓ TỌA ĐỘ (is_active = true)
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO public.irrigation_gate (gate_code, gate_name, waterway_name, source_id, is_demo, is_active, geom)
SELECT
  v.gate_code,
  v.gate_name,
  v.waterway_name,
  s.source_id,
  false,
  true,
  ST_SetSRID(ST_MakePoint(v.longitude, v.latitude), 4326)
FROM public.data_source s,
(VALUES
  ('DTG001', 'Cống Vàm Giồng',  'Rạch Vàm Giồng',       106.547889, 10.302000),
  ('DTG002', 'Cống Gò Công',    'Rạch Vàm Giồng',       106.648889, 10.354444),
  ('DTG003', 'Cống Long Uông',  'Kênh Salisette',        106.705000, 10.322778),
  ('DTG004', 'Cống Tân Thành',  'Kênh Champeaux',        106.734444, 10.275556),
  ('DTG005', 'Cống Cần Lộc',    'Kênh Gò Công Đông',    106.755444, 10.404611),
  ('DTG006', 'Cống Sơn Qui',    'Sông Sơn Quy',          106.684444, 10.395000),
  ('DTG007', 'Cống Rạch Già',   'Rạch Già',              106.658611, 10.310556),
  ('DTG008', 'Cống Bà Tài',     'Rạch Bà Tài',           106.667222, 10.286111),
  ('DTG009', 'Cống Bà Lắm',     'Rạch Bà Lắm',           106.693056, 10.281667),
  ('DTG010', 'Cống Rạch Mương', 'Rạch Mương',            106.659722, 10.253056),
  ('DTG011', 'Cống Lý Quàn',    'Sông Cửa Trung',        106.688333, 10.238056),
  ('DTG012', 'Cống Vàm Tháp',   'Kênh Gò Công Đông',    106.760389, 10.408083)
) AS v(gate_code, gate_name, waterway_name, longitude, latitude)
WHERE s.source_code = 'SLICEGATE_DONGTHAPMOI_2026';

-- ─────────────────────────────────────────────────────────────────────────────
-- INSERT 3 CỐNG PENDING (chưa có tọa độ xác minh — is_active = false)
-- geom đặt tại centroid vùng nghiên cứu (10.36°N 106.37°E) để thoả NOT NULL;
-- KHÔNG dùng các điểm này trong phân tích không gian.
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO public.irrigation_gate (gate_code, gate_name, waterway_name, source_id, is_demo, is_active, geom)
SELECT
  v.gate_code,
  v.gate_name,
  v.waterway_name,
  s.source_id,
  false,
  false,  -- is_active=false: chưa có tọa độ xác minh
  ST_SetSRID(ST_MakePoint(106.370, 10.360), 4326)  -- centroid placeholder
FROM public.data_source s,
(VALUES
  ('DTG013', 'Cống Kênh 14',      'Kênh 14'),
  ('DTG014', 'Cống Cả Thu',       'Rạch Cả Thu'),
  ('DTG015', 'Cống Mương Điều',   'Mương Điều')
) AS v(gate_code, gate_name, waterway_name)
WHERE s.source_code = 'SLICEGATE_DONGTHAPMOI_2026';

-- ─────────────────────────────────────────────────────────────────────────────
-- KIỂM TRA sau khi INSERT
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
  gate_code,
  gate_name,
  waterway_name,
  is_active,
  ROUND(ST_X(geom)::numeric, 6) AS longitude,
  ROUND(ST_Y(geom)::numeric, 6) AS latitude,
  ST_SRID(geom)                 AS srid
FROM public.irrigation_gate
WHERE gate_code LIKE 'DTG%'
ORDER BY gate_code;

-- ─────────────────────────────────────────────────────────────────────────────
-- Tổng hợp
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
  COUNT(*)                                   AS tong_cong,
  COUNT(*) FILTER (WHERE is_active = true)   AS co_toa_do,
  COUNT(*) FILTER (WHERE is_active = false)  AS pending
FROM public.irrigation_gate
WHERE gate_code LIKE 'DTG%';

-- ─────────────────────────────────────────────────────────────────────────────
-- ĐỔI DÒNG DƯỚI THÀNH COMMIT KHI ĐÃ XEM KẾT QUẢ VÀ XÁC NHẬN ĐÚNG
-- Sau đó chạy LẠI TOÀN BỘ FILE từ BEGIN đến COMMIT
-- ─────────────────────────────────────────────────────────────────────────────
ROLLBACK;
