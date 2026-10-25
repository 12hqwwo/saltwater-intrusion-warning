import { $, node, sourceAnchor } from "../shared/ui.js";
import { dateOnly } from "../research-utils.js";
import { requestJSON } from "../api.js";

export function renderOverview(summary) {
  $("modeBadge").textContent = summary.storage_mode === "postgres" ? "PostgreSQL" : "Snapshot có nguồn";
  $("statRia").textContent = summary.ria2_observations;
  $("statSites").textContent = summary.stations;
  $("statLatest").textContent = summary.latest_observed_date ? dateOnly(summary.latest_observed_date) : "Chưa có";
  $("observationCoverage").textContent = `${summary.observations} số đo trong nguồn đang chọn`;
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
