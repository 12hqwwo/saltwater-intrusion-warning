"""Transcribe the 34 monitoring sites and four EC campaigns from the supplied PDF.

The tables below are a checked transcription of PDF pages 1-5, 8, 12, 16,
19 and 23. Keep the printed coordinates and EC strings intact alongside the
parsed values. This script does not infer the calendar dates of campaigns I-IV.
"""

from __future__ import annotations

import argparse
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "gis" / "tiengiang_monitoring" / "monitoring_records.json"
PILOT_CODES = {"NM26", "NM28", "NM29", "NM30", "NM31", "NM32", "NM33", "NM34"}

# code | PDF site name | longitude DMS | latitude DMS | PDF page
SITES = """
NM1|Vàm Cái Bè – huyện Cái Bè|106°02'0,35"|10°19'28"|1
NM2|Cửa sông Ba Rài – huyện Cai Lậy|106°03'48"|10°19'24"|1-2
NM3|Bến phà Ngũ Hiệp – sông Năm Thôn – huyện Cai Lậy|106°07'0,3"|10°18'16,08"|2
NM4|Khu vực chế biến thủy sản (KCN Mỹ Tho)|106°20'3,4"|10°20'44,7"|2
NM5|Bến Chương Dương – thành phố Mỹ Tho|106°21'44"|10°21'11,8"|2
NM6|Cảng Cá Mỹ Tho – Phường 8 – thành phố Mỹ Tho|106°22'21,6"|10°20'30,6"|2
NM7|Cống Vàm Giồng – sông Tiền – huyện Gò Công Tây|106°32'52,4"|10°18'7,2"|2
NM8|Cầu Cổ Cò – huyện Cái Bè|106°54'54"|10°20'2"|2
NM9|Cầu thị trấn Cái Bè – huyện Cái Bè|106°1'55,2"|10°20'17,2"|2
NM10|Chợ Cẩm Sơn – huyện Cai Lậy|106°4'55,1"|10°22'30,7"|2
NM11|Hội Xuân Cai Lậy – huyện Cai Lậy|106°4'21"|10°19'23"|2
NM12|Cầu thị xã Cai Lậy|106°07'02"|10°24'20,0"|3
NM13|Kênh 12 – cầu Quản Oai – Nguyễn Văn Tiếp – thị xã Cai Lậy|106°05'38,5"|10°289'44,0"|3
NM14|Kênh 7 – Nguyễn Văn Tiếp – huyện Cái Bè|105°57'56,9"|10°30'32,3"|3
NM15|Kênh 5 – Nguyễn Văn Tiếp – huyện Cái Bè|105°58'26,4"|10°30'33,0"|3
NM16|Cầu Mỹ Phước – chùa Phật Đá – kênh Nguyễn Văn Tiếp – huyện Tân Phước|106°11'33,3"|10°28'33,5"|3
NM17|Kênh Trương Văn Sanh – Vàm Cỏ Tây – huyện Tân Phước|105°11'14,12"|10°31'38,3"|3
NM18|Cầu Phú Mỹ – kênh Nguyễn Văn Tiếp – huyện Tân Phước|106°19'59,0"|10°32'25,00"|3
NM19|Kênh Bắc Đông – Vàm Cỏ Tây – huyện Tân Phước|106°11'48,0"|10°34'53,5"|3
NM20|Kênh Tràm Mù – Vàm Cỏ Tây – huyện Tân Phước|106°8,0'35"|10°33'8,5"|3
NM21|Cầu Thạnh Phú – huyện Châu Thành|105°18'15,2"|10°22'22,9"|3-4
NM22|Cầu Bình Đức – thành phố Mỹ Tho|106°27'17,9"|10°21'2,6"|4
NM23|Cầu Hùng Vương – thành phố Mỹ Tho|106°21'53,0"|10°21'58,4"|4
NM24|Ngã ba Rạch Ông Đạo – sông Bảo Định – huyện Châu Thành|106°22'50,4"|10°27'40,6"|4
NM25|Cầu Chợ Gạo – huyện Chợ Gạo|106°28'0,6"|10°21'21,6"|4
NM26|Kênh Chợ Gạo (cống Đồng Sơn) – sông Tra – huyện Gò Công Tây|106°04'7,7"|10°24'48,0"|4
NM27|Cầu Bình Phan – huyện Chợ Gạo|106°34'44,9"|10°20'42,9"|4
NM28|Cầu thị trấn Vĩnh Bình – huyện Gò Công Tây|106°28'45,2"|10°21'3,7"|4
NM29|Cầu Rạch Nhiếm – huyện Tân Phú Đông|106°38'16,0"|10°16'8,9"|4
NM30|Cầu Long Chánh – thị xã Gò Công|106°40'13,8"|10°21'4,2"|4
NM31|Cầu Tân Hòa – thị trấn Tân Hòa – huyện Gò Công Đông|106°42'35,6"|10°19'14,0"|4-5
NM32|Cống Cần Lộc – huyện Gò Công Đông|106°45'19,6"|10°24'16,6"|5
NM33|Cống Vàm Tháp – xã Tân Phước – huyện Gò Công Đông|106°45'37,4"|10°24'29,1"|5
NM34|Cầu Lý Quàn – xã Phú Đông – huyện Tân Phú Đông|106°41'48,0"|10°14'49,1"|5
""".strip()

# code | EC campaign I | II | III | IV, all as printed in µS/cm
EC = """
NM1|6.100|359|193,4|49,6
NM2|7.100|435|195|60,3
NM3|9.500|601|317|70,9
NM4|9.920|708|204|72,2
NM5|12.060|913|207,8|128
NM6|12.030|1.077|209,6|133
NM7|16.860|2.037|1.987|62,2
NM8|625|329|229|62,2
NM9|5.400|367|209|69
NM10|2.500|414|193,4|157,6
NM11|3.050|539|263|117,1
NM12|1.900|1.610|409|120,8
NM13|930|1.377|326|93,9
NM14|620|835|275|75,7
NM15|630|947|274|80,3
NM16|1.220|1.956|399|102,4
NM17|680|1.574|578|127
NM18|1.167|1.821|400|158
NM19|701|1.785|356|155
NM20|638|1.797|524|128
NM21|3.020|2.360|621|113,8
NM22|9.860|736|343|95,1
NM23|9.960|775|231|71,5
NM24|1.311|1.149|816|205
NM25|1.056|9.000|632|88,3
NM26|19.330|2.970|378|319
NM27|2.790|2.159|584|75,4
NM28|3.730|2.020|553|66,6
NM29|24.700|18.580|8850|3.810
NM30|6.040|7.060|416|215,2
NM31|17.700|16.890|369|263
NM32|46.100|40.700|1092|697
NM33|34.300|21.180|986|603
NM34|15.220|33.000|2330|937
""".strip()

EC_PAGES = {**{f"NM{i}": 8 for i in range(1, 8)},
            **{f"NM{i}": 12 for i in range(8, 17)},
            **{f"NM{i}": 16 for i in range(17, 21)},
            **{f"NM{i}": 19 for i in [21, 22, 23, 24, 25, 27]},
            **{f"NM{i}": 23 for i in [26, 28, 29, 30, 31, 32, 33, 34]}}

POSITION_REVIEW = {
    "NM8": "Kinh độ in trong báo cáo lệch xa địa danh Cái Bè; cần đối chiếu bản đồ gốc.",
    "NM17": "Kinh độ 105°11′ in trong báo cáo lệch khỏi cụm Tân Phước; cần đối chiếu.",
    "NM21": "Kinh độ 105°18′ in trong báo cáo lệch khỏi cụm Châu Thành; cần đối chiếu.",
    "NM22": "Bảng 1 trang 4 in kinh độ 106°27′, nhưng bản đồ Phụ lục 1 trang 26 đặt NM22 phía tây NM4 tại Mỹ Tho; cần xác minh vị trí gốc.",
    "NM26": "Kinh độ 106°04′ in trong báo cáo lệch khỏi cụm Gò Công; không dùng để tính khoảng cách trước khi xác minh.",
    "NM27": "Bảng 1 trang 4 đặt NM27 phía đông NM28, trái với thứ tự hai điểm trên bản đồ Phụ lục 1 trang 26; khả năng hoán đổi tọa độ cần xác minh.",
    "NM28": "Tọa độ in cách Cầu Chợ Gạo (NM25) khoảng 1,46 km; bản đồ Phụ lục 1 trang 26 đặt NM28 phía đông NM27. Khả năng hoán đổi cần xác minh.",
    "NM33": "Tọa độ in cách NM32 khoảng 0,66 km, nhưng Phụ lục 1 trang 26 đặt NM33 ở phía bắc, tách khỏi NM32; cần xác minh.",
}
FORMAT_REVIEW = {
    "NM20": "Kinh độ in 106°8,0′35″ có phút dạng thập phân không thông thường; giá trị 8,0 phút vẫn phân tích được, cần kiểm tra bản ghi gốc.",
}
# Candidate coordinates inferred from Table 1 and the relative positions in
# Appendix 1 (PDF p. 26). These are hypotheses, never survey-verified values.
CANDIDATE_COORDINATES = {
    "NM8": ("105°54'54\"", "10°20'2\"", "DEGREE_DIGIT_106_TO_105",
            "Đổi riêng chữ số độ kinh 106→105; Phụ lục 1 đặt NM8 ở phía tây Cái Bè."),
    "NM17": ("106°11'14,12\"", "10°31'38,3\"", "DEGREE_DIGIT_105_TO_106",
             "Đổi riêng chữ số độ kinh 105→106; Phụ lục 1 đặt NM17 cùng dải với NM16/NM19 tại Tân Phước."),
    "NM21": ("106°18'15,2\"", "10°22'22,9\"", "DEGREE_DIGIT_105_TO_106",
             "Đổi riêng chữ số độ kinh 105→106; Phụ lục 1 đặt NM21 phía tây Mỹ Tho."),
    "NM27": ("106°28'45,2\"", "10°21'3,7\"", "POSSIBLE_NM27_NM28_ROW_SWAP",
             "Lấy cặp số in ở dòng NM28; Phụ lục 1 đặt NM27 gần NM25 tại Chợ Gạo."),
    "NM28": ("106°34'44,9\"", "10°20'42,9\"", "POSSIBLE_NM27_NM28_ROW_SWAP",
             "Lấy cặp số in ở dòng NM27; Phụ lục 1 đặt NM28 tại Gò Công Tây."),
}
DMS_RE = re.compile(r"^(\d+)°\s*(\d+(?:,\d+)?)'\s*(\d+(?:,\d+)?)\"$")


def dms_to_decimal(value: str, limit: int) -> float | None:
    match = DMS_RE.fullmatch(value)
    if not match:
        return None
    degrees, minutes, seconds = (Decimal(part.replace(",", ".")) for part in match.groups())
    if degrees > limit or not 0 <= minutes < 60 or not 0 <= seconds < 60:
        return None
    return float(degrees + minutes / 60 + seconds / 3600)


def parse_ec(value: str) -> Decimal:
    # The report uses a dot for thousands and a comma for decimals.
    result = Decimal(value.replace(".", "").replace(",", "."))
    if result < 0:
        raise ValueError(value)
    return result


def build(pdf_path: Path) -> dict:
    digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    locations = []
    for line in SITES.splitlines():
        code, name, lon_raw, lat_raw, page = line.split("|")
        longitude = dms_to_decimal(lon_raw, 180)
        latitude = dms_to_decimal(lat_raw, 90)
        status = "INVALID_DMS" if longitude is None or latitude is None else (
            "REVIEW_POSITION" if code in POSITION_REVIEW else (
                "REVIEW_FORMAT" if code in FORMAT_REVIEW else "DMS_TRANSCRIBED"))
        locations.append({
            "site_code": code, "site_name": name,
            "longitude_dms_raw": lon_raw, "latitude_dms_raw": lat_raw,
            "longitude_deg": longitude, "latitude_deg": latitude,
            "coordinate_status": status,
            "coordinate_note": POSITION_REVIEW.get(code, FORMAT_REVIEW.get(
                code, "" if status != "INVALID_DMS" else "DMS trong PDF không hợp lệ; chưa tạo geometry.")),
            "pilot_go_cong": code in PILOT_CODES,
            "coordinate_pdf_page": page,
            "ec_pdf_page": EC_PAGES[code],
        })

    observations = []
    ec_by_site = {}
    for line in EC.splitlines():
        code, *raw_values = line.split("|")
        if len(raw_values) != 4:
            raise ValueError(f"Expected four EC values for {code}")
        ec_by_site[code] = {}
        for campaign, raw in zip(("I", "II", "III", "IV"), raw_values):
            value = parse_ec(raw)
            ms_m = value / Decimal(10)
            ec_by_site[code][campaign] = float(ms_m)
            observations.append({
                "site_code": code, "campaign": campaign,
                "ec_us_cm_raw": raw,
                "ec_us_cm": float(value),
                "ec_ms_m": float(ms_m),
                "ec_pdf_page": EC_PAGES[code],
                "campaign_date": None,
            })
    for location in locations:
        location.update({f"ec_{campaign}_ms_m": ec_by_site[location["site_code"]][campaign]
                         for campaign in ("I", "II", "III", "IV")})

    by_code = {row["site_code"]: row for row in locations}
    candidates = []
    for code, (lon_dms, lat_dms, method, reason) in CANDIDATE_COORDINATES.items():
        source = by_code[code]
        lon = dms_to_decimal(lon_dms, 180)
        lat = dms_to_decimal(lat_dms, 90)
        assert lon is not None and lat is not None
        candidates.append({
            "site_code": code,
            "site_name": source["site_name"],
            "source_longitude_dms_raw": source["longitude_dms_raw"],
            "source_latitude_dms_raw": source["latitude_dms_raw"],
            "candidate_longitude_dms": lon_dms,
            "candidate_latitude_dms": lat_dms,
            "candidate_longitude_deg": lon,
            "candidate_latitude_deg": lat,
            "candidate_method": method,
            "candidate_status": "INFERRED_NOT_VERIFIED",
            "candidate_reason": reason,
            "source_coordinate_pdf_page": source["coordinate_pdf_page"],
            "comparison_map_pdf_page": 26,
        })

    expected = {f"NM{i}" for i in range(1, 35)}
    assert {row["site_code"] for row in locations} == expected
    assert {row["site_code"] for row in observations} == expected
    assert len(locations) == 34 and len(observations) == 136
    assert sum(row["pilot_go_cong"] for row in locations) == 8
    assert {row["site_code"] for row in locations if row["pilot_go_cong"] and row["coordinate_status"] == "REVIEW_POSITION"} == {"NM26", "NM28", "NM33"}
    assert {row["site_code"] for row in locations if row["coordinate_status"] != "DMS_TRANSCRIBED"} == {"NM8", "NM13", "NM17", "NM20", "NM21", "NM22", "NM26", "NM27", "NM28", "NM33"}
    assert {row["site_code"] for row in candidates} == {"NM8", "NM17", "NM21", "NM27", "NM28"}
    assert next(row for row in observations if row["site_code"] == "NM26" and row["campaign"] == "I")["ec_ms_m"] == 1933
    return {
        "source_pdf_sha256": digest,
        "source_pdf_name": pdf_path.name,
        "source_notes": "No unambiguous sampling dates for campaigns I-IV. Coordinates are Table 1 transcriptions, not survey-verified positions. PDF page 2 keeps longitude (106°) in the left coordinate column and latitude (10°) in the right column.",
        "crs": "EPSG:4326",
        "ec_conversion": "mS/m = µS/cm / 10",
        "locations": locations,
        "observations": observations,
        "coordinate_candidates": candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build(args.pdf)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for filename, rows in (
        ("locations_34.csv", result["locations"]),
        ("ec_campaigns_136.csv", result["observations"]),
        ("pilot_go_cong_8.csv", [row for row in result["locations"] if row["pilot_go_cong"]]),
        ("coordinate_hypotheses_5.csv", result["coordinate_candidates"]),
    ):
        with (args.output.parent / filename).open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    print(f"Wrote {len(result['locations'])} locations and {len(result['observations'])} EC records to {args.output}")


if __name__ == "__main__":
    main()
