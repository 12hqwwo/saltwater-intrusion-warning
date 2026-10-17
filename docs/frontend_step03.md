# Frontend hiện tại

`frontend/research.html` là trang chính với bản đồ trạm, biểu đồ quan trắc, đối chiếu dự báo tháng, nguồn dữ liệu, hồ sơ cống và tiếp nhận riêng. `frontend/index.html` đọc lịch sử PostgreSQL.

```powershell
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
```

Xem [hướng dẫn chạy](run_guide.md). Không có lớp phân bố mặn liên tục hoặc lịch vận hành tự động.
