import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const dir = path.dirname(fileURLToPath(import.meta.url));
const wb = Workbook.create();
const summary = wb.worksheets.add("Summary");
const top = wb.worksheets.add("Top errors");
const seasons = wb.worksheets.add("Dry and non-dry");
const high = wb.worksheets.add("High EC");
const font = "Arial";

async function importRows(filename) {
  const csv = await fs.readFile(path.join(dir, filename), "utf8");
  const temp = await Workbook.fromCSV(csv, { sheetName: "Data" });
  return temp.worksheets.getItem("Data").getUsedRange().values;
}

function typedRows(rows) {
  const numeric = new Set(["rank", "high_ec_threshold_mS_m", "actual_mS_m", "random_forest_mS_m",
    "signed_error_mS_m", "abs_error_mS_m", "persistence_abs_error_mS_m",
    "seasonal_naive_abs_error_mS_m", "climatology_abs_error_mS_m", "prior_month_ec_mS_m",
    "next_month_ec_mS_m", "sample_count", "n", "mae_mS_m", "rmse_mS_m", "bias_mS_m"]);
  const header = rows[0].map(String);
  return [header, ...rows.slice(1).map(row => row.map((v, i) => {
    const value = v == null ? "" : String(v);
    if (numeric.has(header[i]) && value !== "") return Number(value);
    if (value === "True") return "Có";
    if (value === "False") return "Không";
    return value;
  }))];
}

function populate(sheet, rows, widths) {
  sheet.showGridLines = false;
  const values = typedRows(rows);
  const labels = { station: "Trạm", split: "Tập", rank: "Hạng", target_month: "Tháng",
    season: "Mùa", high_ec: "EC cao", high_ec_threshold_mS_m: "Ngưỡng EC", actual_mS_m: "EC đo",
    random_forest_mS_m: "RF dự báo", signed_error_mS_m: "Sai số có dấu", abs_error_mS_m: "Sai số tuyệt đối",
    persistence_abs_error_mS_m: "Persistence lỗi", seasonal_naive_abs_error_mS_m: "Naive lỗi",
    climatology_abs_error_mS_m: "Climatology lỗi", prior_month_ec_mS_m: "EC tháng trước",
    next_month_ec_mS_m: "EC tháng sau", sample_count: "Số mẫu", source_qa: "QA nguồn",
    weather_input_month: "Tháng thời tiết", assumed_weather_available_at: "Ngày giả định có dữ liệu",
    source_review: "Duyệt nguồn", model: "Mô hình", n: "Số tháng", mae_mS_m: "MAE",
    rmse_mS_m: "RMSE", bias_mS_m: "Bias", segment: "Nhóm" };
  values[0] = values[0].map(name => labels[name] ?? name);
  sheet.getRangeByIndexes(0, 0, values.length, values[0].length).values = values;
  sheet.getRangeByIndexes(0, 0, values.length, values[0].length).format.font = { name: font, size: 10, color: "#253245" };
  const header = sheet.getRangeByIndexes(0, 0, 1, values[0].length);
  header.format = { fill: "#19365A", font: { name: font, size: 10, bold: true, color: "#FFFFFF" }, rowHeight: 25 };
  header.format.horizontalAlignment = "center";
  for (let i = 0; i < widths.length; i++) sheet.getRangeByIndexes(0, i, values.length, 1).format.columnWidth = widths[i];
  sheet.freezePanes.freezeRows(1);
  return values;
}

const topRows = populate(top, await importRows("top_errors.csv"),
  [13, 13, 7, 15, 9, 9, 20, 16, 22, 19, 16, 23, 23, 23, 21, 21, 14, 16, 20, 24, 16]);
const seasonRows = populate(seasons, await importRows("season_metrics.csv"),
  [13, 13, 10, 23, 7, 16, 17, 17]);
const highRows = populate(high, await importRows("high_ec_metrics.csv"),
  [13, 13, 13, 23, 23, 7, 16, 17, 17]);
top.getRange(`G2:P${topRows.length}`).setNumberFormat("0.00");
seasons.getRange(`F2:H${seasonRows.length}`).setNumberFormat("0.00");
high.getRange(`G2:I${highRows.length}`).setNumberFormat("0.00");

summary.showGridLines = false;
summary.tabColor = "#19365A";
summary.getRange("A2").values = [["Kiểm tra sai số dự báo EC theo trạm"]];
summary.getRange("A2").format.font = { name: font, size: 15, bold: true, color: "#19365A" };
summary.getRange("A3").values = [["Bản mô hình 20261023T041813Z; EC tính bằng mS/m; 120 tháng chấm."]];
summary.getRange("A3").format.font = { name: font, size: 10, italic: true, color: "#52657B" };
summary.getRange("A5:F5").values = [["Trạm", "Tập chấm", "Mùa", "Số tháng", "RF MAE", "RF bias"]];
const rf = seasonRows.slice(1).filter(r => r[1] === "holdout" && r[3] === "RandomForest");
summary.getRange("A6:F9").values = rf.map(r => [r[0], r[1], r[2] === "dry" ? "Mùa khô" : "Ngoài mùa khô", r[4], r[5], r[7]]);
summary.getRange("A12:G12").values = [["Trạm", "Tập chấm", "Nhóm", "Ngưỡng EC", "Số tháng", "RF MAE", "Naive MAE"]];
const highRf = highRows.slice(1).filter(r => r[2] === "high_ec" && r[4] === "RandomForest");
const highNaive = highRows.slice(1).filter(r => r[2] === "high_ec" && r[4] === "SeasonalNaive");
summary.getRange("A13:G16").values = highRf.map((r, i) => [r[0], r[1], "EC cao", r[3], r[5], r[6], highNaive[i][6]]);
summary.getRange("A19").values = [["Mùa khô: tháng 12–4; ngoài mùa khô: 5–11. EC cao: EC đo ≥ phân vị 90 của tập huấn luyện."]];
summary.getRange("A20").values = [["Bảng chi tiết: 15 tháng sai số RandomForest lớn nhất cho mỗi trạm và mỗi tập chấm."]];
summary.getRange("A21").values = [["927/927 tháng khớp bản xuất MRC; cấp duyệt nguồn: Unverified data."]];
summary.getRange("A1:G21").format.font.name = font;
summary.getRange("A1:G21").format.font.size = 10;
summary.getRange("A2").format.font = { name: font, size: 15, bold: true, color: "#19365A" };
for (const address of ["A5:F5", "A12:G12"]) summary.getRange(address).format = {
  fill: "#19365A", font: { name: font, size: 10, bold: true, color: "#FFFFFF" }, rowHeight: 25
};
summary.getRange("E6:F9").setNumberFormat("0.00");
summary.getRange("D13:D16").setNumberFormat("0.0");
summary.getRange("F13:G16").setNumberFormat("0.00");
for (const [col, width] of Object.entries({ A: 16, B: 16, C: 18, D: 14, E: 13, F: 14, G: 14 }))
  summary.getRange(`${col}1:${col}21`).format.columnWidth = width;

wb.recalculate();
for (const [name, range] of [["Summary", "A1:G21"], ["Top errors", "A1:K12"],
  ["Dry and non-dry", "A1:H12"], ["High EC", "A1:I12"]]) {
  const result = await wb.inspect({ kind: "table", sheetId: name, range, maxChars: 800, tableMaxRows: 4, tableMaxCols: 9 });
  console.log(name, result.ndjson.slice(0, 800));
}
const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!", options: { useRegex: true, maxResults: 20 }, maxChars: 800 });
console.log("errors", errors.ndjson.slice(0, 800));
for (const [name, range, file] of [["Summary", "A1:G21", "summary_preview.png"], ["Top errors", "A1:K12", "top_preview.png"],
  ["Dry and non-dry", "A1:H12", "season_preview.png"], ["High EC", "A1:I12", "high_preview.png"]]) {
  const preview = await wb.render({ sheetName: name, range, scale: 1, format: "png" });
  await fs.writeFile(path.join(dir, file), new Uint8Array(await preview.arrayBuffer()));
}
const output = await SpreadsheetFile.exportXlsx(wb);
await output.save(path.join(dir, "multivariate_error_audit.xlsx"));
