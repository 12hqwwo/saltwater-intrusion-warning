# ETL dữ liệu nguồn

Dùng `python etl/etl_csv.py --help` từ gốc repository. Mặc định tạo chuẩn hóa, rejects, checksum và SQL, chỉ ghi PostgreSQL khi chọn `--load`. Không thay dữ liệu nguồn.

Nguồn EC nằm tại `data/raw/ec/mrc/`; metadata và lịch sử nhập được giữ trong `source_manifest.csv` và các báo cáo lịch sử. Contract master CSV cũ có 13 cột; bản phân tích lịch sử có thêm `tide_max_m` không được nhập như cùng contract. Dùng pipeline nghiên cứu hiện tại và `scripts/import_research_workspace.py` để nhập snapshot.

Xem [hướng dẫn Windows](../run_guide.md) và [bàn giao](../handover.md). Các ghi nhận nhập DB trước đây là lịch sử, không xác nhận DB trên máy hiện tại.
