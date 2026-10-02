# TỔNG HỢP SỬA ĐỔI CẦN THỰC HIỆN – TUẦN 3

**Project:** WebGIS dự báo xâm nhập mặn và hỗ trợ điều phối vận hành cống thủy lợi tại tỉnh Đồng Tháp mới  
**Bản rà soát:** `TLCN(3).rar`  
**Mục tiêu:** Hoàn thiện các hạng mục còn lại để **khóa Tuần 3** và chuyển sang **Tuần 4 – ERD + PostgreSQL/PostGIS**.

---

## 1. Trạng thái hiện tại

### Các phần đã ổn

- [x] Ranh giới **Đồng Tháp mới** đã được sửa đúng, chỉ gồm:
  - Đồng Tháp cũ
  - Tiền Giang cũ
- [x] Không còn gộp nhầm An Giang/Kiên Giang.
- [x] `stations_observed.geojson` và `stations_synthetic_demo.geojson` đã được tách riêng.
- [x] Tân Châu được xác định đúng vai trò:
  - **Upstream explanatory station**
  - Nằm ngoài vùng nghiên cứu chính.
- [x] Mỹ Tho nằm trong phạm vi Đồng Tháp mới.
- [x] Dữ liệu synthetic đã được chuyển sang thư mục riêng.
- [x] Bộ cống cũ đã được chuyển vào archive và đánh dấu `DO_NOT_USE`.
- [x] Bộ cống mới có:
  - 15 cống
  - 12 cống có tọa độ
  - 3 cống ở trạng thái `Pending`
- [x] 12/12 cống có tọa độ hiện đều nằm trong boundary Đồng Tháp mới.
- [x] Target ML đã được chuyển về **EC – Electrical Conductivity**.
- [x] `train_baseline.py` đã sử dụng `ec_lag_1`, không còn dùng tên biến salinity cho target EC.
- [x] README đã điều chỉnh scope về Đồng Tháp mới.
- [x] Data Inventory đã được cập nhật thêm DAHITI, GloFAS, UHSLC và bộ cống mới.
- [x] Research Workflow về mặt logic hiện đã hợp lý.

---

# 2. BẮT BUỘC SỬA TRƯỚC KHI KHÓA TUẦN 3

## 2.1. Sửa `target_definition.md`

### Lỗi hiện tại

Trong file hiện vẫn có cách quy đổi:

```text
EC (mS/cm) = EC (mS/m) / 10
```

Công thức trên **sai**.

### Quy đổi đúng

```text
1 mS/cm = 100 mS/m
```

Do đó:

```text
EC (mS/cm) = EC (mS/m) / 100
```

Ví dụ:

```text
25 mS/m = 0.25 mS/cm
```

### Hướng xử lý khuyến nghị

Không nên tiếp tục dùng hệ số tuyến tính cố định để chuyển:

```text
EC → Salinity (‰)
```

trong pipeline chính.

Trong phạm vi tiểu luận hiện tại nên thống nhất:

```text
TARGET = Electrical Conductivity
UNIT   = mS/m
```

Toàn bộ các bước sau đều dùng EC:

```text
MRC EC
   ↓
Forecast EC
   ↓
IDW EC
   ↓
EC tại vị trí cống
   ↓
Decision Logic
```

### Nội dung nên thay trong `target_definition.md`

Có thể dùng đoạn sau:

```text
Dữ liệu mục tiêu của nghiên cứu là Electrical Conductivity (EC), đơn vị mS/m.

EC có mối quan hệ với độ mặn nhưng không được xem là đồng nhất với salinity.
Do dữ liệu hiện tại không bảo đảm đầy đủ các điều kiện cần thiết để xây dựng
một phép chuyển đổi EC → độ mặn có độ tin cậy cao, nghiên cứu không sử dụng
một hệ số tuyến tính cố định để chuyển EC sang ‰ trong pipeline dự báo.

Toàn bộ mô hình Temporal Forecasting và Spatial Interpolation sử dụng trực tiếp
EC với đơn vị mS/m.
```

---

## 2.2. Xóa hoặc regenerate `ml_features_dataset.csv`

### File cần kiểm tra

```text
data/processed/ml_features_dataset.csv
```

### Vấn đề hiện tại

File vẫn còn cột:

```text
MyTho_Salinity
```

và có các giá trị được sinh từ logic cũ kiểu:

```text
MyTho_EC = 13.5
MyTho_Salinity = 8.64
```

Đây là artifact cũ và không còn phù hợp với target EC hiện tại.

### Cách sửa

Ưu tiên một trong hai cách:

#### Cách 1 – Nếu file không còn được pipeline sử dụng

Xóa:

```text
data/processed/ml_features_dataset.csv
```

#### Cách 2 – Nếu vẫn cần file này

Regenerate với cấu trúc kiểu:

```text
date
TanChau_Discharge
MyTho_EC
...
```

Không còn:

```text
MyTho_Salinity
```

### Yêu cầu

Toàn bộ dataset processed phải thống nhất:

```text
Target = EC
Unit   = mS/m
```

---

## 2.3. Sửa `generate_synthetic_ec.py`

### Lỗi 1 – Sai đường dẫn output

Script hiện vẫn output về:

```text
data/raw/hydrological/synthetic_ec_data.csv
```

Trong khi cấu trúc mới đã tách synthetic data riêng.

### Sửa thành

```python
OUT_CSV = ROOT / "data" / "synthetic" / "synthetic_ec_data.csv"
```

---

### Lỗi 2 – Sai/không thống nhất đơn vị

Synthetic hiện dùng biến dạng:

```text
ec_value_mS_cm
```

trong khi target thật của project dùng:

```text
mS/m
```

### Sửa thành

```text
ec_value_mS_per_m
```

hoặc tên tương đương nhưng phải nhất quán toàn project.

### Nguyên tắc

Dữ liệu synthetic phải dùng cùng unit với dữ liệu thật:

```text
mS/m
```

Không nên để:

```text
Observed = mS/m
Synthetic = mS/cm
```

vì rất dễ merge nhầm hoặc tạo lỗi scale.

---

## 2.4. Hoàn thiện Study Area Map

### Hiện trạng

Đã có:

```text
docs/diagrams/01_study_area_map.md
```

nhưng chưa có bản đồ thực tế.

### Cần tạo

```text
docs/diagrams/01_study_area_map.qgz
docs/diagrams/01_study_area_map.png
```

### Layer nên có

1. `dong_thap_boundary.geojson`
2. `stations_observed.geojson`
3. Bộ 12 cống có tọa độ
4. Basemap
5. Sông/kênh nếu có
6. Tên địa danh chính nếu cần

### Quy tắc hiển thị

#### Mỹ Tho

Hiển thị là:

```text
Observed monitoring station
```

#### Tân Châu

Hiển thị khác symbol và ghi rõ:

```text
Upstream explanatory station
Outside study area
```

#### Synthetic stations

Không nên đưa vào Study Area Map chính.

Nếu cần demo:

- để layer riêng;
- mặc định tắt;
- ghi rõ `Synthetic / Demo`.

### Thành phần bản đồ bắt buộc

- Title
- Legend
- North Arrow
- Scale Bar
- CRS
- Source
- Boundary
- Monitoring stations
- Sluice gates

### CRS

```text
EPSG:4326
WGS84
```

---

## 2.5. Export Research Workflow thành diagram thật

### Hiện trạng

Logic trong:

```text
docs/diagrams/02_research_workflow.md
```

đã ổn.

### Flow được duyệt

```text
MRC EC
Open-Meteo
DAHITI
GloFAS
UHSLC
     ↓
Data Cleaning
     ↓
Monthly Alignment
     ↓
Master Timeseries
     ↓
EDA / Lag Analysis
     ↓
Forecast EC at Stations
     ↓
Spatial Interpolation – IDW
     ↓
Estimate EC at Sluice Gates
     ↓
Decision Logic
     ↓
FastAPI
     ↓
Leaflet WebGIS
```

### Cần xuất thành

```text
docs/diagrams/02_research_workflow.drawio
docs/diagrams/02_research_workflow.png
```

Có thể dùng:

- diagrams.net / draw.io
- Mermaid rồi export PNG/SVG

---

# 3. CẦN SỬA PHẦN DECISION THRESHOLD

## 3.1. Chưa nên dùng bảng threshold hiện tại

Không nên giữ các dòng dạng:

```text
Lúa nhạy cảm       1–2‰
Lúa chịu mặn vừa   2–4‰
```

nếu nguồn trích dẫn chưa trực tiếp hỗ trợ đúng các ngưỡng đó.

---

## 3.2. TCVN 8641:2011

Không nên mô tả tiêu chuẩn này là:

```text
Tiêu chuẩn chất lượng nước tưới
```

Nên ghi đúng phạm vi của tiêu chuẩn.

Tại thời điểm Tuần 3, tốt nhất **chưa dùng TCVN này để gán ngưỡng đóng/mở cống**.

---

## 3.3. QCVN 08:2023/BTNMT

Có thể dùng làm tài liệu tham khảo về chất lượng nước mặt nhưng không nên suy ra trực tiếp:

```text
QCVN 08:2023 → lúa chịu mặn 2–4‰
```

nếu quy chuẩn không quy định trực tiếp như vậy.

---

## 3.4. Cách ghi an toàn ở Tuần 3

Trong `target_definition.md` nên ghi:

```text
Decision threshold:
TO BE DEFINED IN WEEK 8

Threshold sẽ được xác định dựa trên:
- mục đích sử dụng nước;
- tài liệu vận hành công trình;
- tài liệu chuyên ngành về khả năng chịu mặn của cây trồng;
- dữ liệu EC/salinity thực tế nếu có;
- quy định/tiêu chuẩn hiện hành phù hợp.
```

### Quan trọng

Tuần 3 **chưa cần khóa threshold cuối cùng**.

Decision Logic chính thức thuộc giai đoạn sau.

---

# 4. CẬP NHẬT NGUỒN VỀ NƯỚC SINH HOẠT

Nếu vẫn giữ phần chất lượng nước sinh hoạt, cần kiểm tra lại quy chuẩn hiện hành.

Không nên tiếp tục dùng một quy chuẩn cũ như nguồn duy nhất nếu đã có phiên bản thay thế.

Tuy nhiên, với phạm vi hiện tại, có thể đơn giản hóa:

```text
Decision Logic tập trung vào mục đích vận hành công trình phục vụ kiểm soát mặn
và cấp nước cho sản xuất nông nghiệp.
```

Nếu không nghiên cứu cấp nước sinh hoạt thì **nên bỏ phần threshold sinh hoạt** để giảm phạm vi.

---

# 5. TÁCH RÕ OBSERVED VÀ SYNTHETIC

Phần này đã làm đúng nhưng cần tiếp tục giữ nguyên quy tắc.

## Observed

```text
stations_observed.geojson
```

Gồm:

```text
Tân Châu
Mỹ Tho
```

Trong đó:

```text
Tân Châu = upstream explanatory station
Mỹ Tho   = observed station inside study area
```

---

## Synthetic

```text
stations_synthetic_demo.geojson
data/synthetic/synthetic_ec_data.csv
```

Các điểm synthetic chỉ được dùng để:

- kiểm thử API;
- kiểm thử WebGIS;
- kiểm thử IDW;
- demo thuật toán;
- kiểm tra giao diện.

Không dùng chúng để kết luận:

```text
phân bố mặn thực tế trên toàn tỉnh Đồng Tháp
```

---

# 6. BỘ CỐNG – QUY TẮC SỬ DỤNG

## Bộ active

Chỉ sử dụng:

```text
sluice_gates_dong_thap_new.csv
sluice_gates_dong_thap_new.geojson
```

## Bộ cũ

Giữ trong:

```text
data/archive/
```

và đánh dấu:

```text
DO_NOT_USE
```

Không để code chính tham chiếu đến bộ cống legacy.

---

## Confidence

Tiếp tục giữ các trường:

```text
coordinate_status
confidence
coordinate_method
source_1
source_2
verification_note
```

### Ý nghĩa

```text
High
= tọa độ có nguồn trực tiếp

High-derived
= suy ra từ quan hệ tuyến thủy văn/công trình có nguồn

Medium
= vị trí hợp lý nhưng cần rà vệ tinh

Pending
= chưa đủ bằng chứng để khóa tọa độ
```

### Không được

Tự điền tọa độ cho các điểm `Pending` nếu chưa có bằng chứng.

---

# 7. CẬP NHẬT DATA INVENTORY VÀ DATA DICTIONARY

Kiểm tra lại để đảm bảo các tài liệu metadata khớp 100% với file thực tế.

## Data Inventory cần có riêng các nguồn

- MRC
- Open-Meteo
- DAHITI
- GloFAS
- UHSLC
- GADM / boundary
- Observed stations
- Synthetic stations
- Sluice gates

## Mỗi nguồn nên có

```text
dataset_id
source_name
variable
station/location
unit
spatial_resolution
temporal_resolution
start_date
end_date
file_path
status
role_in_model
notes
```

---

# 8. SỬA THUẬT NGỮ TRONG EDA

Nếu chart đang plot:

```text
conductivity_mS_per_m
```

không nên đặt title là:

```text
Độ mặn Mỹ Tho
```

### Sửa thành

```text
Độ dẫn điện EC tại Mỹ Tho
```

Ví dụ:

```text
Đối chiếu biến động lưu lượng Tân Châu
và độ dẫn điện EC tại Mỹ Tho
```

Nguyên tắc:

```text
EC ≠ Salinity
```

Không dùng hai thuật ngữ thay thế nhau trong báo cáo.

---

# 9. README – KIỂM TRA CUỐI

README cần phản ánh đúng:

```text
Project:
WebGIS dự báo xâm nhập mặn và hỗ trợ điều phối vận hành cống
tại tỉnh Đồng Tháp mới
```

Tân Châu phải ghi:

```text
Upstream explanatory station outside study area
```

Không ghi:

```text
study area = Tân Châu + Mỹ Tho
```

Nếu các nguồn như GloFAS đã tải xong thì không còn ghi:

```text
đang tải
running in background
pending download
```

---

# 10. BẢO MẬT PROJECT

Khi đóng gói để nộp hoặc gửi:

## Giữ

```text
.env.example
```

## Không gửi

```text
.env
```

`.gitignore` có thể đã đúng nhưng khi tạo `.rar/.zip` thủ công vẫn phải kiểm tra để tránh đưa `.env` vào archive.

---

# 11. CHECKLIST KHÓA TUẦN 3

Chỉ chuyển sang Tuần 4 khi tất cả các mục dưới đây đều hoàn tất.

## Data

- [x] Raw data tách riêng.
- [x] Interim / processed tách riêng.
- [x] Synthetic data tách riêng.
- [x] Target là EC.
- [x] Đơn vị target là mS/m.
- [ ] Không còn artifact Salinity sai trong processed data.
- [ ] Synthetic EC đã đổi về mS/m.

## GIS

- [x] Boundary Đồng Tháp mới chính xác.
- [x] CRS EPSG:4326.
- [x] Observed stations riêng.
- [x] Synthetic stations riêng.
- [x] Sluice gates mới.
- [x] Bộ cống cũ archive.
- [ ] Study Area Map hoàn chỉnh.

## Metadata

- [x] Data Inventory có.
- [x] Data Dictionary có.
- [ ] `target_definition.md` sửa xong.
- [ ] Inventory/Dictionary khớp hoàn toàn file hiện tại.

## Diagram

- [ ] `01_study_area_map.png`
- [ ] `02_research_workflow.drawio`
- [ ] `02_research_workflow.png`

## Code

- [x] Baseline forecast sử dụng EC.
- [ ] `generate_synthetic_ec.py` sửa output path.
- [ ] Synthetic generator dùng mS/m.
- [ ] Không còn code chính tạo `salinity_ppt` từ hệ số tuyến tính cố định.

---

# 12. THỨ TỰ SỬA ĐỀ XUẤT

Nên thực hiện theo đúng thứ tự:

## Bước 1

Sửa:

```text
target_definition.md
```

- target = EC;
- unit = mS/m;
- bỏ conversion EC → salinity tuyến tính;
- chưa chốt Decision Threshold.

## Bước 2

Xóa/regenerate:

```text
data/processed/ml_features_dataset.csv
```

Không còn `MyTho_Salinity`.

## Bước 3

Sửa:

```text
generate_synthetic_ec.py
```

Output:

```text
data/synthetic/
```

Unit:

```text
mS/m
```

## Bước 4

Regenerate các output EDA có liên quan.

Đảm bảo title/label đều dùng:

```text
EC / Electrical Conductivity
```

## Bước 5

Tạo:

```text
01_study_area_map.qgz
01_study_area_map.png
```

## Bước 6

Export:

```text
02_research_workflow.drawio
02_research_workflow.png
```

## Bước 7

Rà lại:

```text
README
Data Inventory
Data Dictionary
```

để bảo đảm toàn bộ project đồng bộ.

---

# 13. ĐIỀU KIỆN ĐỂ CHUYỂN SANG TUẦN 4

Khi hoàn tất toàn bộ các mục trên, có thể **khóa Tuần 3**.

Tuần 4 bắt đầu với:

```text
ERD
+
PostgreSQL
+
PostGIS
```

Các bảng dự kiến:

```text
monitoring_station
sluice_gate
ec_observation
forecast_result
gate_recommendation
```

Spatial field nên sử dụng:

```text
geometry(Point, 4326)
```

và sau đó bổ sung:

```text
GiST spatial index
```

---

# KẾT LUẬN

Bản `TLCN(3)` hiện đã đi đúng hướng và phần GIS nền tảng đã tương đối sạch.

Các việc còn lại để hoàn thành Tuần 3 chủ yếu tập trung vào:

1. **Loại bỏ hoàn toàn logic EC → salinity sai**
2. **Dọn artifact processed cũ**
3. **Chuẩn hóa synthetic EC về mS/m**
4. **Hoàn thiện Study Area Map**
5. **Export Research Workflow**
6. **Chưa chốt Decision Threshold nếu chưa có nguồn đủ mạnh**

Sau khi hoàn thành các mục trên, project có thể chuyển sang giai đoạn thiết kế CSDL không gian trong Tuần 4 mà không cần quay lại sửa cấu trúc dữ liệu nền.
