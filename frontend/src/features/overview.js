import { $, node, num, sourceAnchor } from "../shared/ui.js";
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
    node("p", "Mức cảnh báo EC trên sông và cống là mô phỏng tham khảo; cần đo nước tại chỗ trước khi quyết định lấy nước.", "subtle"));
  const grid = node("div", undefined, "quick-scenarios-grid");
  const scenarios = [
    { title: "Mùa khô · 04/2024", description: "So sánh mức cảnh báo EC dọc sông và tại cống trong khung mô phỏng mùa khô.", action: "Xem mùa khô →", detail: { month: "2024-04" } },
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
  mountFreshnessPanel();
  $("modeBadge").textContent = summary.storage_mode === "postgres" ? "PostgreSQL" : "Snapshot có nguồn";
  $("statRia").textContent = summary.ria2_observations;
  $("statSites").textContent = summary.stations;
  $("statLatest").textContent = summary.latest_observed_date ? dateOnly(summary.latest_observed_date) : "Chưa có";
  $("observationCoverage").textContent = `${summary.observations} số đo trong nguồn đang chọn`;
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

const freshnessLabels = {
  ERA5_MYTHO: "ERA5 · Mỹ Tho", ERA5_TANCHAU: "ERA5 · Tân Châu",
  ERA5_MYTHUAN: "ERA5 · Mỹ Thuận", KRATIE_Q: "Lưu lượng Kratie",
  TANCHAU_STAGE: "Mực nước Tân Châu", MRC_EC_MYTHO: "EC quan trắc Mỹ Tho",
};

export function freshnessText(key, item) {
  const status = { FRESH: "Còn hạn", DUE: "Sắp cần cập nhật", STALE: "Đã quá hạn", UNAVAILABLE: "Thiếu dữ liệu" }[item.status] || "Chưa rõ";
  const latest = item.last_observation || item.last_source_month || "chưa có";
  const target = item.next_target_month_supported ? ` · Dự báo đến ${item.next_target_month_supported}` : "";
  return `${freshnessLabels[key] || key}: ${status} · Nguồn mới nhất ${latest}${target}`;
}

function mountFreshnessPanel() {
  if ($("dataFreshnessPanel")) return;
  const workflow = document.querySelector(".workflow-cards");
  if (!workflow) return;
  const panel = node("section", undefined, "panel");
  panel.id = "dataFreshnessPanel";
  panel.dataset.view = "overview";
  panel.hidden = Boolean(location.hash && !['#overview', '#main'].includes(location.hash));
  panel.append(node("h3", "Độ tươi dữ liệu đầu vào"),
    node("p", "Ngày khả dụng của khí tượng và thủy văn là giả định cuối tháng + 5 ngày; ngày tải về không phải ngày công bố đầu tiên.", "subtle"));
  const list = node("div"); list.id = "dataFreshnessList";
  list.textContent = "Đang kiểm tra nguồn…";
  panel.append(list);
  $("quickSpatialScenarios")?.after(panel);
}

export async function loadDataFreshness(options) {
  mountFreshnessPanel();
  const list = $("dataFreshnessList");
  if (!list) return;
  try {
    const report = await requestJSON('/data-freshness', options);
    list.replaceChildren();
    for (const [key, item] of Object.entries(report.sources || {})) {
      const row = node("p", freshnessText(key, item));
      row.dataset.status = item.status;
      list.append(row);
    }
  } catch (error) {
    list.textContent = `Không kiểm tra được độ tươi nguồn: ${error.message}`;
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
