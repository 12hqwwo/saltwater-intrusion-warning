-- DOC README truoc. Chay sau khi 2 measurement_site da co, DB da sao luu.
-- Toa do trich nguyen van tu 2 KML da cung cap; trang thai REPORTED.
-- Mac dinh ROLLBACK: xem ket qua, chua luu. Neu dung thi doi dong CUOI thanh COMMIT
-- va chay lai TOAN BO file. Script khong ghi de toa do khac da co.
BEGIN;
SET LOCAL search_path=public,pg_catalog;
DO $guard$ BEGIN
 IF current_database()<>'dongthap_gis' THEN
  RAISE EXCEPTION 'Can database dongthap_gis';
 END IF;
END $guard$;
CREATE TEMP TABLE expected_site_location ON COMMIT DROP AS
SELECT * FROM (VALUES
 ('MRC_VN_019803','019803',105.2480164::double precision,10.80062008::double precision,
  'KML Conductivity.Water Quality@VN_019803_[Tan Chau]__station-location.kml; sha256=0059e16ddb527081958707e10c5e62c8fb2fe3df1511dc9c0ab7f12776550867'),
 ('MRC_VN_019805','019805',106.3529997::double precision,10.35912163::double precision,
  'KML Conductivity.Water Quality@VN_019805_[My Tho]__station-location.kml; sha256=a1dc49953943d14d78cb0afff426289d7558c9dc37ea01b4e5c2fd09c33c0644')
) AS e(site_code,external_site_code,longitude,latitude,reference);
DO $guard$ BEGIN
 IF (SELECT count(*) FROM expected_site_location e JOIN public.measurement_site s USING(site_code)
     JOIN public.data_source d ON d.source_id=s.source_id
     WHERE s.external_site_code=e.external_site_code AND s.country_code='VN'
       AND d.source_code='MRC_WATER_QUALITY' AND NOT s.is_demo)<>2 THEN
  RAISE EXCEPTION 'Can dung 2 tram MRC va dung ma; nap raw My Tho truoc';
 END IF;
 IF EXISTS(SELECT 1 FROM expected_site_location e JOIN public.measurement_site s USING(site_code)
           WHERE s.geom IS NOT NULL AND NOT ST_Equals(s.geom,ST_SetSRID(ST_MakePoint(e.longitude,e.latitude),4326))) THEN
  RAISE EXCEPTION 'Da co toa do khac KML; can doi chieu, khong ghi de';
 END IF;
END $guard$;
UPDATE public.measurement_site s
SET geom=ST_SetSRID(ST_MakePoint(e.longitude,e.latitude),4326),
    location_status='REPORTED',location_reference=e.reference
FROM expected_site_location e
WHERE s.site_code=e.site_code AND s.geom IS NULL AND s.location_status='UNKNOWN'
RETURNING s.site_code,s.location_status,ST_X(s.geom) AS longitude,ST_Y(s.geom) AS latitude;
SELECT s.site_code,s.location_status,ST_X(s.geom) AS longitude,ST_Y(s.geom) AS latitude,
       ST_SRID(s.geom) AS srid,s.location_reference
FROM public.measurement_site s JOIN expected_site_location e USING(site_code) ORDER BY s.site_code;
ROLLBACK;
