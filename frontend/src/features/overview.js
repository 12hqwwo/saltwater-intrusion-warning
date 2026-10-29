import { $, node, num, sourceAnchor } from "../shared/ui.js";
import { dateOnly } from "../research-utils.js";
import { requestJSON } from "../api.js";

export function renderOverview(summary) {
  $("modeBadge").textContent = summary.storage_mode === "postgres" ? "PostgreSQL" : "Snapshot có nguồn";
  $("statRia").textContent = summary.ria2_observations;
  $("statSites").textContent = summary.stations;
  $("statLatest").textContent = summary.latest_observed_date ? dateOnly(summary.latest_observed_date) : "Chưa có";
  $("observationCoverage").textContent = `${summary.observations} số đo trong nguồn đang chọn`;
  $("overviewForecastStatus").textContent = summary.live_forecast_available
    ? "Có dự báo đang được cung cấp; xem tháng phát hành và độ tin cậy trong mục Dự báo EC."
    : "Chưa có dự báo EC vận hành đã kiểm định. Kết quả mô hình trong mục Dự báo EC là nghiên cứu; không dùng làm lệnh cống.";
  $("workspaceSourceStatus").textContent = summary.storage_mode === "postgres"
    ? "Quan trắc đọc trực tiếp PostgreSQL/PostGIS. Mỗi trạm dùng một phiên bản dữ liệu được chọn rõ; thí nghiệm và danh mục cống đọc từ bộ tài liệu nghiên cứu."
    : "Quan trắc đọc từ bộ dữ liệu đóng gói có nguồn. Có thể tra cứu phiên bản PostgreSQL trong mục Quan trắc.";
  $("datasetSummary").replaceChildren();
  for (const dataset of (summary.datasets || []).filter(item => item.selected)) {
    $("datasetSummary").append(node("p", `${dataset.site_code} · ${dataset.dataset_code} · ${dataset.observation_count} số đo`, "subtle"));
  }
  $("sourceList").replaceChildren();
  for (const source of summary.sources || []) {
    const card = node("div", undefined, "source-card");
    card.append(
      node("strong", source.provider || source.source_name || source.source_id),
      node("p", source.reference || source.source_id),
      sourceAnchor(source, "Mở nguồn công bố ↗"),
      node("small", `Nguồn: ${source.source_id}`),
    );
    if (source.retrieved_at) card.append(node("small", `Ngày thu thập: ${dateOnly(source.retrieved_at)}`));
    $("sourceList").append(card);
  }
}

export function renderOverviewStations(collection) {
  const host = $("overviewEcTable");
  host.replaceChildren();
  const stations = (collection?.features || []).map(feature => feature.properties || {})
    .filter(item => Number.isFinite(item.latest_ec_mS_m) && item.last_observed_date)
    .sort((a, b) => String(b.last_observed_date).localeCompare(String(a.last_observed_date)) || String(a.site_code).localeCompare(String(b.site_code)));
  if (!stations.length) {
    $("overviewEcStatus").textContent = "Chưa có mẫu EC hợp lệ để tóm tắt.";
    return;
  }
  const table = node("table"), head = node("thead"), header = node("tr"), body = node("tbody");
  for (const label of ["Trạm", "Mẫu EC gần nhất (mS/m)", "Ngày đo", "Xem lịch sử"]) header.append(node("th", label));
  head.append(header);
  for (const item of stations.slice(0, 8)) {
    const row = node("tr");
    row.append(node("td", item.site_name || item.site_code), node("td", num(item.latest_ec_mS_m)), node("td", dateOnly(item.last_observed_date)));
    const cell = node("td"), link = node("a", "Mở trạm →");
    link.href = `#observations`;
    link.addEventListener("click", () => window.dispatchEvent(new CustomEvent("workspace:select-station", { detail: { site_code: item.site_code } })));
    cell.append(link); row.append(cell); body.append(row);
  }
  table.append(head, body); host.append(table);
  $("overviewEcStatus").textContent = `Hiển thị ${Math.min(stations.length, 8)}/${stations.length} trạm theo ngày mẫu mới nhất. Các trạm có thể được đo vào ngày khác nhau; đây không phải EC hiện thời.`;
}
export function bindDatabaseCheck() {
  $("checkDatabase").addEventListener("click", async () => {
    $("checkDatabase").disabled = true;
    $("dbStatus").textContent = "Đang kiểm tra PostgreSQL…";
    try {
      await requestJSON("/health");
      $("dbStatus").textContent = "Đã kết nối PostgreSQL. Xem lịch sử ngay trong mục Quan trắc.";
    } catch (error) {
      $("dbStatus").textContent = error.message;
    } finally {
      $("checkDatabase").disabled = false;
    }
  });
}
