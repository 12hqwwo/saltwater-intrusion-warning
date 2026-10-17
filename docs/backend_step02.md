# API hiện tại

Xem [hướng dẫn chạy](run_guide.md) và OpenAPI `/docs` trên máy chủ.

`backend/main.py` đăng ký API lịch sử PostgreSQL, `research.py` phục vụ dữ liệu nghiên cứu và hồ sơ kế hoạch cống, `intake.py` đọc dữ liệu đang rà soát. API DB dùng transaction chỉ đọc và truy vấn tham số hóa. Không tự chuyển nguồn khi lỗi.

Kiểm thử phần mềm và log cũ đã được sao lưu ngoài repository theo yêu cầu bàn giao; xem [biên bản bàn giao](handover.md).
