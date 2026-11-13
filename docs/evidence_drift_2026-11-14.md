# Rà soát bằng chứng tái lập ngày 14/11/2026

Mục F của `docs/on_tap_hoi_dong_2026-11-13/02_kich_ban_demo.md` đã phân loại sáu trường hợp lệch của lần chạy 13/11. Hai test kỳ vọng cũ đã được cập nhật theo mã đang phục vụ: Mỹ Tho 04/2024 lấy từ mô hình chính, và fixture PostgreSQL có `observations=[]`.

## Khôi phục đúng phiên bản nguồn

| Bộ kết quả | Tệp nguồn | SHA-256 trong manifest | Cách khôi phục |
|---|---|---|---|
| `frozen_ec_remedies_20261108` | `scripts/evaluate_frozen_ec_gap_remedies.py` | `dbadaddb5f8ee6cd9cad9abd44fb8cf6f148683e3df7f9178f9fb355ec1851fa` | Bản Git `eba9a0c`, chép byte gốc vào `source_snapshots/scripts/`; không đổi script đang chạy. |
| `mythuan_three_station_20261104` | `scripts/evaluate_mythuan_three_station.py` | `d79fe2c1c0753a712635f201212dca6dbfeb25c4441f2211aa26b117b40f48ac` | Bản Git `9e5d413`, chép byte gốc vào `source_snapshots/scripts/`. |
| `mythuan_three_station_20261104` | `scripts/train_multivariate_ec.py` | `9430ef0904d67b5d2dedd8c365f6c65387a272eae3e74425106a4c4accf1e821` | Bản Git `2af86db`, thay snapshot sai phiên bản; byte gốc khớp manifest. |

Các SHA-256 ở bảng đã được đối chiếu với byte của Git blob trước khi lưu snapshot. Không sửa manifest để ép test đạt.

## Nguồn chưa khôi phục được

`outputs/mythuan_three_station_20261104/run_manifest.json` yêu cầu `data/external/multivariate_weather/manifest.json` có SHA-256 `da9b80d2c54d52a427705d326160b1bacce17e94874ab6e5a757f3e75fd48443`. Bản hiện tại có SHA-256 `97898949f67329bc768f20214806d8f46d0062be11d3336dc334c68ad48110d8`; các snapshot trong bộ kết quả và manifest được Git theo dõi không có byte khớp bản gốc. Vì vậy **chưa thể xác nhận tái lập đầy đủ đầu vào** của bộ Mỹ Thuận. Test đầu ra vẫn kiểm checksum độc lập; test đầu vào đánh dấu skip với tên nguồn thiếu. Không dùng bộ kết quả này làm bằng chứng tái lập chính cho hội đồng cho đến khi tìm được bản manifest gốc hoặc chạy lại thí nghiệm với manifest/nguồn mới được khóa.

Việc sửa test và snapshot không thay đổi mô hình, registry hay số liệu trên WebGIS.

## Kiểm tra sau sửa

`scripts/check.ps1 -Full` ngày 14/11/2026: **117 test Python, 0 FAIL, 0 ERROR, 1 skip** (test hash đầu vào của bộ Mỹ Thuận vì thiếu manifest khí tượng gốc); 32 test Node trong smoke pass. Số test Python tăng từ 116 lên 117 do tách kiểm checksum đầu ra thành một test độc lập để nó vẫn chạy khi test nguồn phải skip. `scripts/check.ps1` thường: 21 Python và 32 Node pass.
