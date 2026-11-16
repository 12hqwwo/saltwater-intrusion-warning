## Phần 1. Cây thư mục tổng quan

Ký hiệu: `[CHẠY WEB]` = được dùng khi trang web đang chạy; `[CHẠY TAY]` = chỉ dùng khi người chạy lệnh; `[DỮ LIỆU]` = nơi cất dữ liệu/bằng chứng, không phải mã. Thư mục chứa rất nhiều file cùng loại được tóm lại bằng `...`; danh sách đầy đủ có ở Phần 2.

```text
D:\Study\TLCN\
├── start.ps1                        [CHẠY WEB] Nút khởi động: build rồi chạy web
├── start-tinbranch.ps1              [CHẠY TAY] Chạy một worktree khác bằng cấu hình chính
├── run_webgis.py                    [CHẠY WEB] Nạp .env, chọn nguồn, bật máy chủ
├── run_monthly_ec.py                [CHẠY TAY] Thí nghiệm dự báo EC tháng kiểu cũ
├── run_gate_advisor.py              [CHẠY TAY] Chấm hồ sơ cống từ dòng lệnh
├── run_station_gate_link.py         [CHẠY TAY] Đánh giá liên kết trạm–cống
├── requirements*.txt                Danh sách thư viện Python cần cài
├── .env.example                     Mẫu cấu hình máy, không chứa mật khẩu thật
├── .env                             Cấu hình thật của máy, KHÔNG mở/commit
├── .gitignore / .gitattributes      Quy định Git bỏ qua/xử lý file nào
├── README.md                        Giới thiệu và cách chạy dự án
├── CLAUDE.md                        Biên bản bàn giao cho phiên làm việc sau
├── DESIGN.md                        Nguyên tắc thiết kế giao diện
├── REPO_MAP_FOR_THESIS.md           Bản đồ repo cũ, thiên về báo cáo
│
├── backend/                         [CHẠY WEB] Bếp: máy chủ Python FastAPI
│   ├── main.py                      Cửa chính: tạo app, gắn mọi API
│   ├── database.py                  Mở kết nối đọc PostgreSQL
│   ├── db_security.py               Kiểm tra tài khoản DB đúng vai trò
│   ├── security.py                  Lớp chặn request lạ, thêm header an toàn
│   ├── schemas.py                   Khuôn dạng JSON trả về cho trạm/EC
│   ├── intake.py                    API tab Chất lượng dữ liệu
│   ├── research.py                  Đường dẫn cũ /api/v1/research giữ tương thích
│   ├── requirements-api.txt         Thư viện riêng cho phần API
│   ├── api/                         Người nhận order: định nghĩa đường dẫn API
│   │   ├── workspace.py             Bản đồ, timeline, cống, xuất dữ liệu
│   │   ├── multivariate.py          Dự báo EC: catalog, inputs, predict
│   │   ├── dss_storage.py           Lưu/đọc lịch sử dự báo, bản nháp cống
│   │   ├── gate_screening.py        Rà soát điều kiện lấy nước qua cống
│   │   ├── forecast_issues.py       Sổ phát hành dự báo hằng tháng
│   │   ├── field_measurements.py    Phiếu EC thực địa: gửi, duyệt
│   │   └── data_freshness.py        Báo dữ liệu nguồn cũ hay mới
│   ├── services/                    Bếp trưởng: điều phối từng chức năng
│   │   ├── workspace.py             Tổng hợp trạm, quan trắc, cống
│   │   ├── spatial_inputs.py        Ghép EC 3 trạm theo tháng, lấp tháng thiếu
│   │   ├── spatial_simulation.py    Dựng khung bản đồ: sông màu, chấm cống
│   │   ├── multivariate.py          Ghép đầu vào rồi gọi mô hình dự báo
│   │   ├── forecasts.py             Biểu đồ hồi cứu, ước tính tháng cũ
│   │   ├── gates.py                 Chấm hồ sơ cống
│   │   ├── dss_storage.py           Kiểm tra rồi lưu dự báo/bản nháp
│   │   ├── forecast_issues.py       Phát hành và chấm điểm dự báo tháng
│   │   └── field_measurements.py    Nhận và duyệt phiếu thực địa
│   ├── domain/                      Đầu bếp làm toán: công thức thuần
│   │   ├── multivariate_ec.py       Nạp Random Forest, kiểm hash, dự báo
│   │   ├── river_interpolation.py   Nội suy tuyến tính EC dọc sông
│   │   ├── gates.py                 Luật chấm hồ sơ cống
│   │   ├── gate_intake_rules.py     Luật rà soát lấy nước (bản máy chủ)
│   │   ├── gate_simulation.py       Mô phỏng trạng thái cống theo luật
│   │   ├── ec_gap_*.py              Đọc kết quả thí nghiệm khóa EC
│   │   ├── forecast_issue.py        Lịch phát hành và cách chấm điểm
│   │   ├── field_measurement.py     Chuẩn hóa phiếu EC thực địa
│   │   ├── data_freshness.py        Tính độ trễ dữ liệu nguồn
│   │   └── workspace.py             Kiểm tra gói dữ liệu snapshot
│   └── repositories/                Thủ kho: đọc/ghi DB và file
│       ├── workspace.py             Đọc PostgreSQL hoặc workspace.json
│       ├── multivariate_inputs.py   Đọc khí tượng ERA5 theo tháng
│       ├── hydrology_inputs.py      Đọc lưu lượng Kratie, mực nước Tân Châu
│       ├── dss_storage.py           Ghi/đọc bảng lưu dự báo, bản nháp
│       ├── forecast_issues.py       Ghi/đọc bảng phát hành dự báo
│       └── field_measurements.py    Ghi/đọc bảng phiếu thực địa
│
├── frontend/                        [CHẠY WEB] Phòng ăn: giao diện trình duyệt
│   ├── workspace.html               Trang chính năm tab
│   ├── index.html / research.html   Trang cũ, tự chuyển sang workspace.html
│   ├── package.json                 Khai báo Vite và OpenLayers
│   ├── vite.config.js               Cấu hình đóng gói trang web
│   ├── scripts/generate-river-diagram.mjs  Vẽ sơ đồ sông SVG
│   ├── public/                      Font chữ, sơ đồ sông tĩnh
│   ├── dist/                        Bản đã build, máy chủ phục vụ (tự sinh)
│   └── src/
│       ├── api.js                   Hàm gọi API chung, có hẹn giờ
│       ├── main.js, map.js, style.css   Mã trang cũ, không trang nào nạp
│       ├── chart.js, intake.js, research-*.js  Biểu đồ, tab Chất lượng dữ liệu
│       ├── app/                     Khung ứng dụng: khởi động, tab, CSS
│       │   ├── workspace.js         Khởi động mọi tab, nối sự kiện
│       │   ├── navigation.js        Chuyển tab theo dấu # trên URL
│       │   ├── legacy.js            Chuyển trang cũ sang workspace.html
│       │   └── *.css                Màu, khoảng cách, bố cục
│       ├── features/                Từng chức năng trên màn hình
│       │   ├── observations*.js     Tab Quan trắc và bản đồ
│       │   ├── timeline-scrubber.js Thanh kéo chọn tháng
│       │   ├── river-*.js, gated-waterways.js, map-particles.js  Vẽ sông, nhánh, hạt chảy
│       │   ├── point-inspection.js  Bấm bản đồ xem giá trị ước tính
│       │   ├── multivariate-forecast.js, prediction-history.js  Tab Dự báo
│       │   ├── forecasts.js, next-forecast.js, forecast-issue-panel.js  Hồi cứu, sổ phát hành
│       │   ├── gate-*.js            Tab Hồ sơ cống
│       │   ├── field-measurements.js, weather-estimates.js  Phiếu thực địa, ước tính
│       │   ├── database-history.js  Bảng lịch sử EC PostgreSQL
│       │   └── overview.js          Tab Tổng quan
│       ├── shared/                  Công thức dùng chung cho nhiều tab
│       └── styles/simulation.css    CSS bản đồ mô phỏng
│
├── data/                            [DỮ LIỆU] Kho dữ liệu đầu vào
│   ├── raw/                         Dữ liệu gốc tải về (EC MRC, khí tượng...)
│   ├── external/                    Dữ liệu ngoài theo đợt thu thập
│   ├── research/                    workspace.json, mẫu EC tháng, registry thí nghiệm
│   ├── models/                      multivariate_registry.json, CSV dự báo cũ
│   ├── biengioi/                    Ranh giới hành chính, hành lang sông GeoJSON
│   ├── contracts/                   Khuôn dữ liệu cống, chính sách cống
│   ├── metadata/                    Từ điển dữ liệu, danh mục nguồn
│   ├── 8file/                       Bộ 8 CSV người dùng cung cấp
│   ├── processed/, staging/, features/  Dữ liệu trung gian đã xử lý
│   └── archive/                     Dữ liệu cũ, không dùng
│
├── runs/                            [DỮ LIỆU] Mô hình đã huấn luyện và lần chạy
│   └── multivariate_ec/mytho/20261108T_HYDROLOGY_PRIMARY_V1/  Mô hình Mỹ Tho đang phục vụ
│       ├── model.joblib             Bộ 300 cây Random Forest đã lưu
│       ├── manifest.json            Lý lịch mô hình: đặc trưng, hash, điểm
│       └── predictions.csv          Kết quả dự báo đã lưu
├── outputs/                         [DỮ LIỆU] Bằng chứng thí nghiệm giảm sai số
├── reports/                         [DỮ LIỆU] Biên bản UAT, dọn dẹp repo
│
├── scripts/                         [CHẠY TAY] ~115 kịch bản thu thập, thí nghiệm
│   └── utilities/                   Tải dữ liệu triều FES2022b
├── tools/                           [CHẠY TAY] Lệnh gộp: kiểm tra, huấn luyện, bảo mật (mới)
├── data_collection/                 [CHẠY TAY] Tải GloFAS, DAHITI, UHSLC, ranh giới
├── etl/etl_csv.py                   [CHẠY TAY] Nạp CSV vào DB kiểu cũ
├── sql/                             [CHẠY TAY] Lệnh tạo bảng, quyền PostgreSQL
│   ├── checks/                      Truy vấn kiểm tra hiện trạng DB
│   └── migrations/                  Lệnh nâng cấp cấu trúc DB
├── config/                          Cấu hình tải FES, GloFAS
├── tests/                           Bài kiểm tra tự động frontend + backend
│   └── fixtures/                    Dữ liệu mẫu cho test
└── docs/                            Tài liệu, báo cáo LaTeX, ôn tập
    ├── bao_cao_webgis_ec_mytho_2026_11_08/  Báo cáo đồ án LaTeX
    ├── on_tap_hoi_dong_2026-11-13/  Bộ ôn tập bảo vệ
    ├── project_map/                 Tài liệu bạn đang đọc
    └── *.md                         Ghi chép từng đợt thí nghiệm, hướng dẫn
```

Thư mục do máy tự sinh, không cần học: `.venv/`, `.venv-api/` (môi trường Python), `frontend/node_modules/` (thư viện JavaScript), `frontend/dist/` (bản build), `__pycache__/`.
