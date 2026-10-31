import { $, node, sourceAnchor } from "../shared/ui.js";
import { dateOnly } from "../research-utils.js";
import { requestJSON } from "../api.js";


export function mountQuickScenarios() {
  if ($("quickSpatialScenarios")) return;
  const workflow = document.querySelector(".workflow-cards");
  if (!workflow) return;
  const panel = node("section", undefined, "panel quick-scenarios-panel");
  panel.id = "quickSpatialScenarios";
  panel.dataset.view = "overview";
  panel.hidden = Boolean(location.hash && !['#overview', '#main'].includes(location.hash));
  panel.append(node("span", "KHÁM PHÁ NGUỒN NƯỚC", "tag"), node("h3", "Chọn kịch bản để xem trên bản đồ"),
    node("p", "Đoạn sông, ranh mặn và trạng thái cống là mô phỏng tham khảo; cần đo nước tại chỗ trước khi quyết định lấy nước.", "subtle"));
  const grid = node("div", undefined, "quick-scenarios-grid");
  const scenarios = [
    { title: "Mùa khô · 04/2024", description: "So sánh ranh mặn và trạng thái cống trong khung mô phỏng mùa khô.", action: "Xem mùa khô →", detail: { month: "2024-04" } },
    { title: "Mùa mưa · 10/2022", description: "Khám phá sự thay đổi nguồn nước trên cùng tuyến sông trong mùa mưa.", action: "Xem mùa mưa →", detail: { month: "2022-10" } },
    { title: "Kịch bản sầu riêng", description: "Thử cặp ngưỡng EC minh họa 50/80 mS/m; đây không phải tiêu chuẩn tưới cho mọi vườn.", action: "Áp dụng ngưỡng mẫu →", detail: { preset: "durian" } },
    { title: "Dự báo theo khí tượng", description: "Chọn trạm, xem EC dự báo, phân tán giữa các cây và sai số kiểm định trước khi đưa lên bản đồ.", action: "Mở công cụ dự báo →", view: "forecasts" },
  ];
  for (const scenario of scenarios) {
    const card = node("article", undefined, "quick-scenario-card");
    const button = node("button", scenario.action, "secondary");
    button.type = "button";
    button.addEventListener("click", () => {
      if (scenario.detail) window.dispatchEvent(new CustomEvent("workspace:simulation-scenario", { detail: scenario.detail }));
      location.hash = scenario.view || "observations";
    });
    card.append(node("h4", scenario.title), node("p", scenario.description, "subtle"), button);
    grid.append(card);
  }
  panel.append(grid);
  workflow.after(panel);
}

export function renderOverview(summary) {
  mountQuickScenarios();
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
  mountQuickScenarios();
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
