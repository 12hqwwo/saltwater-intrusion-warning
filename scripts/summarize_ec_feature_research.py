"""Prepare the EC research report and workbook inputs from saved experiments."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from research_ec_features import EXTERNAL, OUT, ROOT, GROUPS, save_json

LABELS = {
    "rain_memory": "Mưa tích lũy và chuỗi ngày khô",
    "water_balance": "ET0 và chênh lệch mưa - ET0",
    "humidity_radiation": "Độ ẩm, bức xạ, biên độ nhiệt",
    "soil_moisture": "Độ ẩm đất 0-100 cm",
    "wind_direction": "Hướng gió dạng u/v gần đúng",
    "enso": "ENSO Niño 3.4",
}
CATALOG = [
    ["EC quá khứ", "ec_latest, ec_previous, ec_lag12, ec_mean3/12, ec_age_months", "mS/m, tháng", "MRC tại Mỹ Tho và Tân Châu", "1985-2023; 927 mẫu", "Có sẵn", "Biến nền; giữ cờ UNVERIFIED, không xóa cực trị chỉ dựa IQR toàn chuỗi", "Cuối tháng + 0 hoặc 30 ngày, giả định", "https://portal.mrcmekong.org/"],
    ["Mùa vụ", "month_sin, month_cos", "không đơn vị", "Lịch tháng cần dự báo", "500 tháng/trạm", "Tự tính", "Biến nền; biết trước, không cần tải", "Biết trước tại lúc phát hành", ""],
    ["Mưa tích lũy và khô hạn", ", ".join(GROUPS["rain_memory"]), "mm, ngày", "Open-Meteo trong dữ liệu gốc", "1985-01 đến 2026-08; 30.436 ngày-trạm", "Có sẵn, tạo thêm đặc trưng", "Dùng cửa sổ 30/90 ngày; ngày khô <1 mm; là mưa cục bộ, không phải mưa toàn lưu vực", "Ngày đo + 5 ngày, giả định hồi cứu", "https://open-meteo.com/en/docs/historical-weather-api"],
    ["ET0 và cân bằng khí hậu", ", ".join(GROUPS["water_balance"]), "mm", "Open-Meteo trong dữ liệu gốc", "1985-01 đến 2026-08", "Có sẵn nhưng pipeline v2 chưa dùng", "ET0 là bốc thoát hơi tham chiếu; mưa-ET0 là chỉ báo khí hậu, không phải cân bằng nước sông", "Ngày đo + 5 ngày, giả định hồi cứu", "https://open-meteo.com/en/docs/historical-weather-api"],
    ["Độ ẩm và bức xạ", ", ".join(GROUPS["humidity_radiation"]), "%, MJ/m2, degC", "Open-Meteo trong dữ liệu gốc", "1985-01 đến 2026-08", "Có sẵn nhưng pipeline v2 chưa dùng", "Tương quan với ET0/nhiệt độ; cần đánh giá đóng góp tăng thêm", "Ngày đo + 5 ngày, giả định hồi cứu", "https://open-meteo.com/en/docs/historical-weather-api"],
    ["Độ ẩm đất", ", ".join(GROUPS["soil_moisture"]), "m3/m3", "ERA5 qua Open-Meteo, models=era5", "1985-01 đến 2026-08; 15.218 ngày/trạm", "Đã tải mới", "Ô đất 0,25 độ; chỉ báo độ ẩm lưu trữ cục bộ, không phải số đo tại cống", "Ngày đo + 5 ngày; chưa có historical vintages", "https://open-meteo.com/en/docs/historical-weather-api"],
    ["Hướng gió", ", ".join(GROUPS["wind_direction"]), "m/s", "ERA5 qua Open-Meteo, models=era5", "1985-01 đến 2026-08; 15.218 ngày/trạm", "Đã tải mới", "u/v gần đúng từ tốc độ trung bình và hướng trội ngày; không phải trung bình vector giờ", "Ngày đo + 5 ngày; chưa có historical vintages", "https://open-meteo.com/en/docs/historical-weather-api"],
    ["ENSO", ", ".join(GROUPS["enso"]), "degC dị thường", "NOAA PSL, ERSST V6 theo footer tệp thực tải", "1948-01 đến 2026-09 trong tệp; dùng phần quá khứ", "Đã tải mới", "Chuẩn 1981-2010; giả thuyết khí hậu gián tiếp, chưa chứng minh hữu ích cho EC từng trạm", "Cuối tháng nguồn + 30 ngày, giả định; kiểm tra đúng ngày lịch", "https://psl.noaa.gov/data/correlation/nina34.anom.data"],
    ["Lưu lượng Tân Châu đo/truy dựng", "gfz_tanchau_q_lag2_m3s, gfz_tanchau_q_mean3_m3s", "m3/s", "GFZ, Apel và cộng sự 2024", "Tệp thực có 1980-2016, 444 tháng", "Đã có bản nguồn và bản chuẩn hóa", "Chỉ thử phần 1996-2016; Mỹ Tho dùng như biến thượng nguồn, không coi là lưu lượng tại Mỹ Tho", "Cuối tháng nguồn + 30 ngày, giả định", "https://doi.org/10.5880/GFZ.4.4.2024.004"],
    ["Lưu lượng GloFAS", "glofas_q_lag4_m3s", "m3/s", "GloFAS cũ Tân Châu; mẫu API mới cho hai vị trí", "Chuỗi cũ 1985-2023; mẫu mới năm 2021", "Có chuỗi cũ và đã tải mẫu mới", "Ô lưới chưa xác minh; API Mỹ Tho trung bình khoảng 5 m3/s cần rà lại sông; mẫu mới không vào mô hình", "Bản consolidated giả định trễ 90 ngày; không dùng như dự báo lưu lượng", "https://open-meteo.com/en/docs/flood-api"],
    ["Mực nước vệ tinh", "dahiti_latest_m, dahiti_age_days", "m, ngày", "DAHITI 627 và 3316 trong dự án", "Độ phủ sau căn thời gian: 136/464 Tân Châu, 184/463 Mỹ Tho", "Có sẵn; thử nghiệm riêng", "Mẫu không đều; không nội suy dài; tọa độ/điểm đại diện và hệ cao độ cần đối chiếu", "Giả định trễ 30 ngày, bỏ nếu số đo quá 90 ngày tuổi", "https://dahiti.dgfi.tum.de/en/627/"],
    ["Mực nước ven biển Vũng Tàu", "vungtau_daily_max_mean30_m", "m", "UHSLC trong dự án", "Chuỗi ngày từ 1985-11; giữ khoảng trống", "Có sẵn; thử nghiệm riêng", "Trung bình cực đại ngày; không phải biên độ triều, không đại diện triều tại cống", "Giả định trễ 90 ngày; cần xác nhận độ trễ sản phẩm", "https://uhslc.soest.hawaii.edu/data/"],
    ["Mưa toàn lưu vực", "area_weighted_rain_30d/90d", "mm", "CHIRPS, ERA5 theo polygon lưu vực", "CHIRPS có dữ liệu từ 1981", "Nguồn đã xác định, chưa tải lớp lưới", "Cần ranh giới lưu vực thượng nguồn và tổng hợp theo diện tích; chưa đánh giá", "Theo từng sản phẩm sơ bộ/chính thức", "https://www.chc.ucsb.edu/data/chirps"],
    ["Nhiệt độ nước và vận hành", "water_temperature, gate_state, reservoir_release", "degC, trạng thái, m3/s", "Số đo trạm, hồ sơ cơ quan quản lý", "Chưa có chuỗi đồng bộ trong bộ EC", "Chưa có bộ dữ liệu đủ dùng", "Không dùng nhiệt độ không khí thay cho nhiệt độ nước hoặc tự quy đổi EC25", "Cần thời điểm đo/công bố thực", ""],
]


def mdtable(frame):
    def cell(v):
        if pd.isna(v): return "—"
        if isinstance(v, float): return f"{v:.3f}"
        return str(v).replace("|", "/")
    return "| " + " | ".join(map(str, frame.columns)) + " |\n| " + " | ".join(["---"] * len(frame.columns)) + " |\n" + "\n".join("| " + " | ".join(cell(v) for v in row) + " |" for row in frame.itertuples(index=False, name=None))


def prepare_summary():
    v = pd.read_csv(OUT / "validation_metrics.csv")
    h = pd.read_csv(OUT / "holdout_metrics.csv")
    hydro = pd.read_csv(OUT / "hydrology_metrics.csv")
    f = pd.read_csv(OUT / "feature_matrix.csv")
    audit = pd.read_csv(OUT / "target_audit.csv")
    main = v[v.ec_delay_days.eq(0) & v.algorithm.eq("RF") & v.configuration.str.startswith("PLUS_")].copy()
    main["feature_group"] = main.configuration.str.replace("PLUS_", "", regex=False)
    main["label"] = main.feature_group.map(LABELS)
    main.to_csv(OUT / "feature_gain_summary.csv", index=False, encoding="utf-8-sig")
    drop = []
    for (station, delay, alg), group in v.groupby(["station", "ec_delay_days", "algorithm"]):
        allrow = group[group.configuration.eq("ALL")]
        if allrow.empty: continue
        for _, row in group[group.configuration.str.startswith("MINUS_")].iterrows():
            drop.append(dict(station=station, ec_delay_days=delay, algorithm=alg,
                             removed_group=row.configuration.removeprefix("MINUS_"), all_mae=float(allrow.mae.iloc[0]),
                             without_mae=row.mae, mae_increase_when_removed=row.mae-float(allrow.mae.iloc[0])))
    pd.DataFrame(drop).to_csv(OUT / "drop_group_summary.csv", index=False, encoding="utf-8-sig")
    pred = pd.read_csv(OUT / "validation_predictions.csv", parse_dates=["target_month"])
    yearly = pred.assign(abs_error=(pred.prediction-pred.actual).abs()).groupby(["station","ec_delay_days","algorithm","configuration","year"], as_index=False).abs_error.mean()
    yearly.to_csv(OUT / "validation_yearly_mae.csv", index=False, encoding="utf-8-sig")
    daily = []
    for station in ["MyTho", "TanChau"]:
        payload = json.loads((EXTERNAL / f"era5_extra_{station}.json").read_text(encoding="utf-8"))
        df = pd.DataFrame(payload["daily"]).rename(columns={"time": "date"})
        df.insert(0,"station",station); df["grid_lat"] = payload["latitude"]; df["grid_lon"] = payload["longitude"]
        df["source"] = "Open-Meteo_ERA5"; daily.append(df)
    pd.concat(daily, ignore_index=True).to_csv(OUT / "candidate_daily_era5.csv", index=False, encoding="utf-8-sig")
    flow = []
    for path in EXTERNAL.glob("glofas_preview*.json"):
        p = json.loads(path.read_text(encoding="utf-8"))
        d = pd.DataFrame(p["daily"]).rename(columns={"time":"date","river_discharge":"river_discharge_m3s"})
        d.insert(0,"station",path.name.split("_")[2]); d["grid_lat"]=p["latitude"]; d["grid_lon"]=p["longitude"]
        d["quality"]="GRID_AND_DEFAULT_MODEL_VERSION_NOT_VALIDATED"; flow.append(d)
    pd.concat(flow, ignore_index=True).to_csv(OUT / "glofas_preview_2021.csv", index=False, encoding="utf-8-sig")
    catalog = pd.DataFrame(CATALOG, columns=["group","features","unit","source","coverage","download_status","limitation","availability","source_url"])
    catalog.to_csv(OUT / "feature_catalog.csv", index=False, encoding="utf-8-sig")
    preview_columns = ["station","target_month","issue_time","ec_target","ec_target_v2","ec_latest","ec_lag12","ec_age_months",
                       "rain_30d_mm","rain_90d_mm","et0_30d_mm","p_minus_et0_90d_mm","humidity_30d_pct","radiation_30d_mj_m2",
                       "soil_moisture_30d_m3_m3","wind_u_proxy_30d_ms","wind_v_proxy_30d_ms","nino34_lag2_c","gfz_tanchau_q_lag2_m3s",
                       "dahiti_latest_m","vungtau_daily_max_mean30_m","weather_observed_through","ec_source_quality"]
    full = f[f.ec_delay_days.eq(0)][preview_columns]
    # Serialize typed numeric/null values for the workbook renderer.
    data = {"catalog": catalog.to_dict("records"), "validation": v.to_dict("records"), "holdout": h.to_dict("records"),
            "hydrology": hydro.to_dict("records"), "gains": main.to_dict("records"), "matrix": full.to_dict("records"),
            "preview": full[full.target_month.between("2023-01-01","2023-12-01")].to_dict("records"),
            "audit": audit.to_dict("records"), "matrix_columns":preview_columns}
    save_json(OUT / "workbook_data.json", data)
    report = """# Nghiên cứu feature dự báo EC theo tháng

Ngày: 19/10/2026. Phạm vi: Mỹ Tho và Tân Châu, dự báo giá trị mẫu EC của tháng kế tiếp. Đây là nghiên cứu hồi cứu và bản xem trước, chưa thay đổi mô hình/API đang phục vụ WebGIS.

## 1. Kết quả cần chú ý

- Hướng gió gần đúng u/v là ứng viên tốt nhất trong nhánh Random Forest Tân Châu: MAE validation giảm khoảng 4,60%, cải thiện cả sáu năm; giai đoạn 2020–2023 giảm khoảng 2,40% so với RF nền. Mức cải thiện nhỏ và chưa qua tiêu chí lợi ích tối thiểu 5% đã đặt trước.
- Độ ẩm đất giảm MAE RF Mỹ Tho khoảng 14,12% ở giả định EC trễ 0 ngày, nhưng khoảng bootstrap còn chứa mức không cải thiện. Với trễ 30 ngày, mức giảm khoảng 21,41% qua bộ lọc thăm dò; vẫn chưa vượt mô hình Ridge chỉ dùng EC và mùa vụ trên validation. Không mặc định triển khai.
- Thêm toàn bộ nhóm biến làm RF xấu hơn ở cả hai trạm trong validation. ET0, mưa tích lũy, độ ẩm/bức xạ và ENSO có cơ sở để thử, nhưng phép thử này chưa chứng minh lợi ích tăng thêm ổn định.
- Mô hình được chọn bằng validation cho Mỹ Tho không thắng Persistence trên 2020–2023 ở giả định trễ EC 0 ngày. Các mẫu EC cao vẫn là điểm yếu lớn.
- Các nhánh lưu lượng/mực nước/ven biển được thử riêng trên cùng tập tháng giữa BASE và PLUS. Chưa có bằng chứng cải thiện mạnh và ổn định, nhiều nguồn còn vấn đề đại diện không gian hoặc thiếu dữ liệu.

## 2. Bộ dữ liệu đã chuẩn bị

`feature_matrix.csv`: 2.000 dòng = 2 trạm × 500 tháng (1985-01 đến 2026-08) × 2 giả định độ trễ EC. Sau 2023 không tự sinh nhãn EC. Khóa ghép là `station + target_month + ec_delay_days`.

`candidate_daily_era5.csv`: 30.436 dòng ngày-trạm mới tải, gồm độ ẩm đất 0–100 cm, tốc độ gió trung bình ngày và hướng gió trội. Yêu cầu ghim `models=era5`; lưu JSON, URL, đơn vị, tọa độ ô trả về và SHA-256.

`noaa_nino34_monthly.csv`: chuỗi Niño 3.4 NOAA, tệp tải ngày 19/10/2026 ghi **ERSST V6**, chuẩn dị thường 1981–2010. Không gắn nhãn V5 theo các trang mô tả cũ. Chỉ dùng các tháng nguồn đủ điều kiện khả dụng khi tạo feature.

`glofas_preview_2021.csv`: 730 dòng ngày-trạm để rà vị trí ô lưới. Bản API trả mặc định, không xác nhận phiên bản trong phản hồi; không đưa mẫu này vào thí nghiệm dự báo. Chuỗi tại ô Mỹ Tho trung bình khoảng 5,02 m3/s là dấu hiệu cần kiểm tra chọn nhánh sông, không tự coi là lưu lượng sông Tiền tại trạm. Nhánh mô hình chỉ thử chuỗi GloFAS Tân Châu cũ và giữ cờ SUSPECT.

`preview_2023.csv`: 24 dòng của hai trạm để xem trước. `feature_catalog.csv`: nguồn, biến, đơn vị, độ phủ, trạng thái tải và giả định khả dụng. Giữ trống khi thiếu; không thay thiếu bằng số 0.

Các biến ET0, độ ẩm không khí và bức xạ đã có đầy đủ trong CSV khí tượng cũ nhưng chưa được pipeline v2 đưa vào. Gió cũ thiếu hồ sơ đơn vị đủ rõ trong CSV nên vẫn dùng nhãn `source_units`, không tự ghi là m/s.

### Xem trước bốn tháng Mỹ Tho

"""
    sample = full[full.station.eq("MYTHO") & full.target_month.between("2023-01-01","2023-04-01")][["target_month","ec_target","ec_latest","rain_30d_mm","et0_30d_mm","soil_moisture_30d_m3_m3","nino34_lag2_c"]]
    report += mdtable(sample) + "\n\nEC mục tiêu chỉ dùng chấm kết quả. Các feature trong cùng dòng được căn theo thời điểm phát hành trước tháng mục tiêu; không phải khí tượng thực tế của tháng tương lai. Ô ENSO trống tháng 3 là do giả định trễ 30 ngày chưa cho phép dùng số tháng 1 vào cuối tháng 2.\n"
    report += """
## 3. Kiểm tra nhãn EC trước khi so sánh

""" + mdtable(audit) + """

Pipeline v2 lọc EC bằng cờ QA `VERIFIED`; bộ quy tắc IQR và biến động được tính trên toàn chuỗi trong mã ETL. Nguồn MRC ban đầu vẫn là `UNVERIFIED`. Vì vậy việc đạt QA kỹ thuật không đồng nghĩa nguồn đã xác minh, và xóa các cực trị dựa trên toàn chuỗi có thể làm mất chính các mẫu cần dự báo.

Nghiên cứu này giữ các mẫu nguồn hữu hạn, không âm trong bộ monthly nghiên cứu, bảo toàn cờ nguồn, và không dùng ngưỡng thống kê toàn chuỗi để bỏ nhãn. Điều đó cũng **không xác nhận 841 mS/m là phép đo đúng**: cần kiểm chứng nguồn/thiết bị cho các giá trị đáng ngờ. Cột `ec_target_v2` được giữ riêng để đối chiếu. Không so trực tiếp MAE ở đây với kết quả trước trên tập nhãn đã lọc.

## 4. Nguồn và lý do chọn feature

""" + mdtable(catalog[["group","source","download_status","source_url"]]) + """

Cơ sở nghiên cứu: [Apel và cộng sự (2020)](https://nhess.copernicus.org/articles/20/1609/2020/) xem xét ENSO và lưu lượng Tân Châu cho xâm nhập mặn theo mùa ở đồng bằng Mekong. [Wullems và cộng sự (2023)](https://hess.copernicus.org/articles/27/3823/2023/) dùng nồng độ chloride quá khứ, mực nước, lưu lượng và gió trong bài toán dự báo cửa sông. Hai nghiên cứu hỗ trợ lựa chọn giả thuyết vật lý; chúng không chứng minh các feature sẽ cải thiện EC tháng tại Mỹ Tho/Tân Châu, và các biến mục tiêu không đồng nhất.

Mưa tại trạm khác mưa toàn lưu vực. Độ ẩm đất và ET0 là chỉ báo điều kiện khí hậu, không phải đo độ dẫn điện hay cân bằng nước sông. Độ dẫn điện còn phụ thuộc ion hòa tan, nhiệt độ nước và cơ sở bù nhiệt; đặc biệt EC thấp ở Tân Châu không nên diễn giải mọi biến động thành nước biển xâm nhập.

GFZ thực có 444 tháng từ 1980 đến 2016 dù tên tệp nói 1964–2017; phần trước 1995 có truy dựng. Chỉ thử đoạn nguồn mô tả là số đo từ 1996. Với Mỹ Tho, cột này mang nghĩa lưu lượng thượng nguồn Tân Châu, không phải số đo tại Mỹ Tho. Dữ liệu độ mặn Sơn Đốc cùng bộ GFZ không được trộn làm nhãn EC.

## 5. Quy trình kiểm chứng đã thực hiện

1. Cố định mục tiêu là mẫu EC tháng M, phát hành cuối tháng M-1. Giữ đơn vị mS/m, không đổi sang độ mặn.
2. Lưu `protocol.json` trước chạy. EC dùng hai giả định cuối tháng +0/+30 ngày. Khí tượng dùng các cửa sổ 30/90 ngày kết thúc trước phát hành 5 ngày. ENSO dùng tháng trễ 2/3/6 và trung bình trượt quá khứ, kiểm tra chính xác điều kiện cuối tháng nguồn +30 ngày. Không dùng cửa sổ giữa tâm có dữ liệu tương lai.
3. Mỗi năm huấn luyện lại bằng các nhãn giả định đã có trước tháng 1, sau đó giữ mô hình trong năm; feature được cập nhật hàng tháng. Train mở rộng từ 1986, tối thiểu 96 nhãn cho nhánh chính.
4. Validation 2014–2019 để so sánh. Khóa lựa chọn trong `selection.json`, rồi mới chấm 2020–2023. Giai đoạn sau đã từng được xem trong dự án nên đây là holdout hồi cứu, không phải kiểm định mù mới.
5. So Persistence, Seasonal Naive, trung bình lịch theo tháng, Random Forest cố định 120 cây và Ridge trên log(1+EC). Điền thiếu và chuẩn hóa học riêng từ train. Không dùng deep learning trên chuỗi tháng ngắn này.
6. BASE = EC quá khứ + mùa vụ + mưa/nhiệt độ/gió hiện có, đã căn thời gian. Thử thêm riêng sáu nhóm, thử ALL và bỏ từng nhóm khỏi ALL. Mọi cấu hình nhánh chính dùng cùng 72 tháng validation và 48 tháng kiểm tra cho mỗi trạm/kịch bản.
7. Chấm MAE, RMSE, bias, MAE tháng 12–4 và các mẫu trên phân vị 90% **của train năm đó**. Ngưỡng này chỉ phục vụ đánh giá mẫu EC cao, không phải ngưỡng cảnh báo vận hành.
8. Tính số năm cải thiện và bootstrap theo block 12 tháng, 1.000 lượt, cho chênh lệch sai số tuyệt đối giữa hai mô hình trên cùng tháng. Tiêu chí thăm dò: giảm MAE ít nhất 5%, thắng ít nhất 4/6 năm, khoảng 95% của lợi ích hoàn toàn dương. Đây là tiêu chí nghiên cứu đặt trước, chưa hiệu chỉnh thử nhiều giả thuyết.
9. Xáo trộn theo nhóm bằng dịch vòng 3/6/9 tháng trên validation của ALL để xem độ nhạy. Đây là chẩn đoán phụ: biến tương quan hoặc mô hình ALL kém có thể làm importance khó diễn giải. Không dùng impurity importance để tuyên bố quan hệ nhân quả.
10. Chạy audit khóa trạm-tháng, thời điểm khả dụng, dữ liệu nguồn không đổi, cùng tập chấm và train trước test. Thay dữ liệu mưa tương lai bằng giá trị cực lớn không làm thay đổi feature của dự báo quá khứ.

## 6. Lợi ích tăng thêm của các nhóm biến

Giả định EC trễ 0 ngày, cùng Random Forest. Phần trăm dương là giảm MAE so với BASE. Đây là validation 2014–2019.

"""
    table = main[["station","label","mae","gain_vs_base_pct","winning_years_vs_base","gain_ci_low","gain_ci_high"]].rename(columns={"label":"Nhóm","gain_vs_base_pct":"Giảm MAE (%)","winning_years_vs_base":"Số năm tốt hơn","gain_ci_low":"CI lợi ích thấp","gain_ci_high":"CI lợi ích cao"})
    report += mdtable(table)
    report += "\n\nKhoảng CI ở bảng có đơn vị mS/m, không phải phần trăm. `drop_group_summary.csv` ghi chênh lệch MAE khi bỏ nhóm khỏi ALL; `group_permutation.csv` ghi chẩn đoán độ nhạy từng nhóm.\n\n### Kiểm tra mô hình đã chọn trên 2020–2023\n\n"
    compact = h[h.ec_delay_days.eq(0)&(h.selected_on_validation.eq(True)|h.configuration.eq("BASE")&h.algorithm.eq("RF")|h.algorithm.eq("PERSISTENCE"))]
    report += mdtable(compact[["station","algorithm","configuration","n","mae","rmse","high_mae"]])
    report += """

Tân Châu: mô hình thêm hướng gió giảm MAE từ khoảng 2,308 xuống 2,253 mS/m so với RF BASE; vẫn có xu hướng dự báo thấp. Mỹ Tho: mô hình Ridge AR được chọn trên validation có MAE khoảng 48,688, kém Persistence 40,848 mS/m; không thể công bố mô hình phức tạp đã tốt hơn baseline ở trạm này. Kết quả có thể chịu ảnh hưởng của các phép đo cao chưa được xác minh.

### Các nhánh thủy văn riêng

""" + mdtable(hydro[["station","study","algorithm","n","start","end","gain_pct"]]) + """

Những bảng này chỉ so BASE và PLUS trong từng dòng/cặp. Không xếp hạng MAE giữa các nguồn vì khoảng thời gian và số mẫu khác nhau. DAHITI Tân Châu thiếu chuỗi mới; dùng tối thiểu 48 nhãn cho nhánh thăm dò này và công bố giới hạn. GloFAS giữ cờ ô lưới chưa xác minh. UHSLC là cực đại mực nước ngày Vũng Tàu, không phải biên độ triều hay dự báo triều tại cống.

## 7. Quyết định đề xuất

- Giữ EC quá khứ và mùa vụ làm lõi. Giữ các baseline trong mọi lần kiểm tra.
- Ưu tiên xác minh các mẫu EC bị loại, đơn vị gió cũ, cơ sở EC/bù nhiệt và tính đại diện không gian; đây có thể quan trọng hơn thêm thuật toán.
- Hướng gió Tân Châu: giữ làm ứng viên, lợi ích nhỏ; cần kiểm chứng thêm các thời kỳ mới trước khi thay mô hình đang dùng.
- Độ ẩm đất Mỹ Tho: giữ làm ứng viên cho nghiên cứu độ trễ, chưa đủ bằng chứng chọn làm cấu hình cuối.
- ET0/khô hạn/ENSO: giữ trong kho dữ liệu để thử các giả thuyết theo mùa hoặc mưa lưu vực; chưa thêm mặc định vào mô hình chính từ kết quả hiện tại.
- Bước dữ liệu tiếp theo có giá trị: mưa tổng hợp theo lưu vực, lưu lượng/mực nước đo có chuỗi mới, nhiệt độ nước và nhật ký vận hành. Phải có tập EC đồng thời để kiểm chứng.
- Khi có dữ liệu sau 2023 đã xác minh: đóng băng cấu hình chọn trước, chấm một giai đoạn mới độc lập, kiểm tra drift và các đợt EC cao. Chỉ sau đó mới quyết định cập nhật API dự báo.

## 8. Tái lập

Chạy từ gốc dự án trong môi trường Python có pandas/numpy/scikit-learn. Không ghi PostgreSQL hay thay WebGIS:

```powershell
python scripts/fetch_ec_feature_candidates.py
python scripts/research_ec_features.py prepare
python scripts/research_ec_features.py evaluate
python scripts/research_ec_hydrology.py
python scripts/check_ec_feature_research.py
python scripts/summarize_ec_feature_research.py
```

Lần tải lại dùng cache các tệp đã có. Muốn snapshot nguồn mới, dùng `--output` cho script tải và tạo nhánh cấu hình nghiên cứu riêng; không ghi đè dữ liệu gốc. Các lần chạy phân tích ghi lại đầu ra trong thư mục nghiên cứu của ngày này. `data_manifest.json`, `download_manifest.json`, `evaluation_manifest.json` giữ checksum và tham số để truy vết.

Giới hạn quan trọng: bản tái phân tích/NOAA tải hôm nay có thể đã được sửa hồi cứu, nên căn độ trễ chưa thay thế kiểm chứng bằng bản dữ liệu thực sự phát hành trong quá khứ. Kết quả là đóng góp dự báo có điều kiện theo tập dữ liệu, mô hình và giai đoạn đã thử; không phải kết luận nhân quả.
"""
    (OUT / "research_report.md").write_text(report, encoding="utf-8")
    print("Prepared report, source catalog, normalized candidate data and workbook inputs.")


def plot():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    table = pd.read_csv(OUT / "feature_gain_summary.csv")
    english = dict(rain_memory="Rain / dry-spell memory", water_balance="ET0 / water-balance proxy", humidity_radiation="Humidity / radiation / temperature", soil_moisture="Soil moisture (0-100 cm)", wind_direction="Wind direction (u/v proxy)", enso="ENSO Nino 3.4")
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.5), sharey=True)
    fig.patch.set_facecolor("#f8fafc")
    order = list(GROUPS)
    for ax, station in zip(axes, ["MYTHO", "TANCHAU"]):
        part = table[table.station.eq(station)].set_index("feature_group").reindex(order)
        values = part.gain_vs_base_pct.to_numpy()
        ax.barh(np.arange(len(order)), values, color=["#137e75" if v>0 else "#bd674b" for v in values], height=.6)
        for i,val in enumerate(values):
            ax.text(val + (0.6 if val>=0 else -0.6), i, f"{val:+.1f}%", ha="left" if val>=0 else "right",va="center",fontsize=10)
        ax.axvline(0, color="#475569",linewidth=.9)
        ax.set_xlim(-32,23); ax.set_title("My Tho" if station=="MYTHO" else "Tan Chau",loc="left",fontweight="bold",pad=14)
        ax.set_yticks(np.arange(len(order)), [english[g] for g in order]); ax.invert_yaxis()
        ax.set_xlabel("MAE reduction vs BASE (%)")
        ax.spines[["top","right","left"]].set_visible(False); ax.grid(axis="x",alpha=.15); ax.set_axisbelow(True)
    fig.suptitle("Which additional features improved monthly EC prediction?",fontsize=15,x=.03,ha="left",fontweight="bold")
    fig.text(.03,.02,"Random Forest | Validation 2014-2019 | EC delay 0 days | Same 72 months per station\nPositive = lower error. Results are retrospective; gains do not establish causality or operational readiness.",fontsize=9,color="#475569")
    fig.tight_layout(rect=[.01,.12,1,.92]); fig.savefig(OUT / "feature_gain.png",dpi=170,facecolor=fig.get_facecolor()); plt.close(fig)
    print("Created feature_gain.png")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--plot-only",action="store_true"); args=parser.parse_args()
    plot() if args.plot_only else prepare_summary()
