/** Build a readable workbook from the checked PDF transcription JSON. */
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { pathToFileURL } from "node:url";

const artifactModule = process.env.CODEX_ARTIFACT_TOOL_MJS;
if (!artifactModule) throw new Error("Set CODEX_ARTIFACT_TOOL_MJS to the bundled artifact_tool.mjs path");
const { Workbook, SpreadsheetFile } = await import(pathToFileURL(artifactModule).href);

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outDir = path.join(root, "data", "processed", "gis", "tiengiang_monitoring");
const data = JSON.parse(await fs.readFile(path.join(outDir, "monitoring_records.json"), "utf8"));
const workbook = Workbook.create();

function addSheet(name, headers, records, widths) {
  const sheet = workbook.worksheets.add(name);
  const cells = [headers, ...records];
  const lastCol = String.fromCharCode(64 + headers.length);
  sheet.getRange(`A1:${lastCol}${cells.length}`).values = cells;
  sheet.getRange(`A1:${lastCol}1`).format = {
    fill: "#135F73", font: { name: "Aptos", bold: true, color: "#FFFFFF" },
  };
  sheet.getRange(`A1:${lastCol}${cells.length}`).format.font = { name: "Aptos", size: 10 };
  sheet.getRange(`A1:${lastCol}1`).format = {
    fill: "#135F73", font: { name: "Aptos", bold: true, color: "#FFFFFF", size: 10 },
  };
  widths.forEach((width, i) => {
    const letter = String.fromCharCode(65 + i);
    sheet.getRange(`${letter}:${letter}`).format.columnWidth = width;
  });
  return sheet;
}

const locRows = rows => rows.map(r => [
  r.site_code, r.site_name, r.longitude_dms_raw, r.latitude_dms_raw,
  r.longitude_deg, r.latitude_deg, r.coordinate_status, r.coordinate_note,
  r.ec_I_ms_m, r.ec_II_ms_m, r.ec_III_ms_m, r.ec_IV_ms_m,
  r.coordinate_pdf_page, r.ec_pdf_page,
]);
const headers = ["Mã", "Tên điểm", "Kinh độ gốc", "Vĩ độ gốc", "Kinh độ °", "Vĩ độ °",
  "QA tọa độ", "Ghi chú QA", "EC I mS/m", "EC II mS/m", "EC III mS/m", "EC IV mS/m",
  "Trang tọa độ", "Trang EC"];
const widths = [9, 44, 19, 19, 16, 16, 22, 66, 14, 14, 14, 14, 14, 12];
addSheet("Pilot Go Cong", headers, locRows(data.locations.filter(r => r.pilot_go_cong)), widths);
addSheet("34 locations", headers, locRows(data.locations), widths);
addSheet("EC I-IV", ["Mã", "Đợt", "EC gốc µS/cm", "EC µS/cm", "EC mS/m", "Trang PDF", "Ngày lấy mẫu"],
  data.observations.map(r => [r.site_code, r.campaign, r.ec_us_cm_raw, r.ec_us_cm,
    r.ec_ms_m, r.ec_pdf_page, r.campaign_date]),
  [10, 10, 20, 17, 17, 13, 18]);
addSheet("Coordinate candidates", ["Mã", "Kinh độ PDF", "Vĩ độ PDF", "Kinh độ giả thuyết",
  "Vĩ độ giả thuyết", "Kinh độ °", "Vĩ độ °", "Phương pháp", "Trạng thái", "Lý do", "Trang bảng", "Trang bản đồ"],
  data.coordinate_candidates.map(r => [r.site_code, r.source_longitude_dms_raw,
    r.source_latitude_dms_raw, r.candidate_longitude_dms, r.candidate_latitude_dms,
    r.candidate_longitude_deg, r.candidate_latitude_deg, r.candidate_method,
    r.candidate_status, r.candidate_reason, r.source_coordinate_pdf_page,
    r.comparison_map_pdf_page]),
  [10, 20, 20, 23, 23, 16, 16, 33, 25, 88, 14, 14]);
addSheet("Readme", ["Mục", "Thông tin"], [
  ["Nguồn", data.source_pdf_name],
  ["SHA-256", data.source_pdf_sha256],
  ["Đổi đơn vị", data.ec_conversion],
  ["Tọa độ", "Chép từ báo cáo; các điểm có cờ QA cần xác minh với nguồn gốc/bản đồ."],
  ["Ngày lấy mẫu", "Không suy đoán ngày của bốn đợt I–IV từ trích đoạn PDF."],
  ["Pilot", "NM26, NM28–NM34; tọa độ NM26, NM28 và NM33 cần xác minh."],
  ["Giả thuyết", "Năm vị trí suy luận từ Bảng 1 và bản đồ Phụ lục 1; chưa phải tọa độ đo đạc gốc."],
], [20, 88]);

workbook.recalculate();
const summary = await workbook.inspect({ kind: "sheet", include: "id,name", maxChars: 2000 });
console.log(summary.ndjson ?? summary);
const preview = await workbook.render({ sheetName: "Pilot Go Cong", range: "A1:H9", scale: 1, format: "png" });
await fs.mkdir(path.join(root, "tmp"), { recursive: true });
await fs.writeFile(path.join(root, "tmp", "tiengiang_pilot_preview.png"), new Uint8Array(await preview.arrayBuffer()));
const output = await SpreadsheetFile.exportXlsx(workbook);
const filename = path.join(outDir, "tiengiang_ec_34.xlsx");
await output.save(filename);
await fs.rm(`${filename}.inspect.ndjson`, { force: true });
console.log(`Saved ${filename}`);
