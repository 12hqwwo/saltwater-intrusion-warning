-- Cống thuộc ranh giới được chọn (tính cả điểm trên biên)
-- Ví dụ: ranh giới DONG_THAP
SELECT g.gate_code, g.gate_name
FROM public.irrigation_gate g
JOIN public.admin_boundary b ON ST_Intersects(g.geom, b.geom)
WHERE b.boundary_code = 'DONG_THAP';

-- Cống trong bán kính tính bằng mét từ một tọa độ gốc (Ví dụ quanh Mỹ Tho 106.3533, 10.3542, bán kính 5000m)
SELECT g.gate_code, g.gate_name,
       ST_Distance(g.geom::geography, ST_SetSRID(ST_MakePoint(106.3533, 10.3542), 4326)::geography) AS dist_m
FROM public.irrigation_gate g
WHERE ST_DWithin(g.geom::geography, ST_SetSRID(ST_MakePoint(106.3533, 10.3542), 4326)::geography, 5000)
ORDER BY dist_m;

-- Kiểm tra hình học và nguồn vị trí sau nhập
SELECT gate_code, gate_name,
       ST_X(geom) AS longitude,
       ST_Y(geom) AS latitude,
       ST_SRID(geom) AS srid,
       ST_IsValid(geom) AS is_valid
FROM public.irrigation_gate;
