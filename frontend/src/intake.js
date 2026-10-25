import { createRequestGate } from "./api.js";
import { workspaceAPI as requestJSON } from "./shared/workspace-api.js";
import { safeExternalURL } from "./research-utils.js";
const cell = (tag, text) => {
  const n = document.createElement(tag);
  n.textContent = text;
  return n;
};
export async function showIntake(host = document.getElementById("intakeHost")) {
  const section = document.createElement("section");
  section.id = "intake";
  section.className = "section panel";
  section.append(cell("h2", "Tiếp nhận và kiểm toán dữ liệu"));
  const status = cell("p", "Đang đọc hồ sơ tiếp nhận…");
  status.setAttribute("role", "status");
  section.append(status);
  host.replaceChildren(section);
  try {
    const [audit, coverage] = await Promise.all([
      requestJSON("/intake"),
      requestJSON("/intake/coverage")
    ]);
    status.className = "notice";
    status.textContent = "Chưa xác minh · Đọc hồ sơ từ tệp · Chưa nhập vào bộ quan trắc hoặc huấn luyện. " + audit.note;
    const counts = audit.counts;
    section.append(cell("p", `${counts.csv_rows} dòng tại ${counts.station_count} trạm; ${counts.next1d_label_count} dòng có nhãn ngày kế tiếp; ${counts.full_hydromet_next1d} dòng có đủ các ô nhãn, triều, mực nước kênh và mưa.`));
    const issues = document.createElement("ul");
    issues.append(cell("li", `${audit.issues.CALENDAR_MISMATCH_feat_salinity_lag1_g_l || 0} lag1 không khớp mẫu đúng ngày trước.`));
    issues.append(cell("li", `${audit.issues.TARGET_REQUIRES_MEASUREMENT_LOCATION_DISAMBIGUATION || 0} dòng cần tách rõ điểm sông và nội đồng trước khi xác định mục tiêu.`));
    issues.append(cell("li", "Số đo 7h, cực đại con triều và cực đại ngày cần chuỗi riêng. Nhãn cùng ngày không phải dự báo ngày mai."));
    section.append(issues);
    const details = document.createElement("details");
    details.append(cell("summary", "Độ phủ theo trạm — tính lại từ tệp v3"));
    const wrap = document.createElement("div");
    wrap.className = "table-wrap";
    const table = document.createElement("table"), head = document.createElement("thead"), heading = document.createElement("tr");
    for (const label2 of ["Mã trạm", "Từ", "Đến", "Ngày có mẫu", "Liên tục dài nhất", "Nhãn ngày kế tiếp"]) heading.append(cell("th", label2));
    head.append(heading);
    table.append(head);
    const body = document.createElement("tbody");
    for (const row of coverage.items) {
      const tr = document.createElement("tr");
      for (const key of ["station", "first", "last", "unique_dates", "longest_daily_run", "next1d_labels"]) tr.append(cell("td", row[key]));
      body.append(tr);
    }
    table.append(body);
    wrap.append(table);
    details.append(wrap);
    section.append(details);
    const files = document.createElement("details");
    files.append(cell("summary", "Tệp tiếp nhận và dấu kiểm tra SHA-256"));
    for (const f of audit.files) {
      const p = cell("p", `${f.file} · ${f.status}`), hash = cell("small", f.sha256);
      hash.style.overflowWrap = "anywhere";
      p.append(document.createElement("br"), hash);
      files.append(p);
    }
    section.append(files);
    const catalogue = await requestJSON("/intake/measurement-points");
    section.append(cell("h3", "Rà soát số đo theo vị trí"));
    section.append(cell("p", `${catalogue.counts.records} giá trị được giữ nguyên trong bảng rà soát; ${catalogue.counts.rejected} ô không đủ điều kiện chuẩn hóa được giữ trong nhật ký loại. Không gán ô trống thành 0.`));
    const label = cell("label", "Điểm đo trong bộ v3"), select = document.createElement("select");
    const positionLabels = { RIVER_REPORTED: "Sông", INTERIOR_0M: "Nội đồng · tại cống/cầu", INTERIOR_200M: "Nội đồng · cách 200 m" };
    for (const p of catalogue.items) {
      const option = cell("option", `${p.name} · ${positionLabels[p.position]} · ${p.records} bản ghi`);
      option.value = p.key;
      select.append(option);
    }
    label.append(select);
    section.append(label);
    const observationStatus = cell("p", ""), observationWrap = document.createElement("div");
    observationStatus.setAttribute("role", "status");
    observationWrap.className = "table-wrap";
    section.append(observationStatus, observationWrap);
    const requests = createRequestGate();
    async function loadPoint() {
      const req = requests.next();
      observationWrap.replaceChildren();
      observationStatus.textContent = "Đang đọc bản ghi chưa xác minh…";
      try {
        const data = await requestJSON("/intake/observations?point=" + encodeURIComponent(select.value), req);
        if (!req.isCurrent()) return;
        observationStatus.textContent = `${data.items.length}/${data.total} bản ghi · g/L · UNVERIFIED · chưa dùng huấn luyện hoặc vận hành.`;
        const table2 = document.createElement("table"), head2 = document.createElement("thead"), row = document.createElement("tr");
        for (const title of ["Ngày ghi trong nguồn", "Giờ / kỳ đo", "Chế độ đo", "Độ mặn (g/L)", "Nguồn và vị trí dòng"]) row.append(cell("th", title));
        head2.append(row);
        table2.append(head2);
        const body2 = document.createElement("tbody");
        for (const r of data.items) {
          const row2 = document.createElement("tr");
          for (const value of [r.observed_date, r.source_time_or_period, r.measurement_regime, r.value]) row2.append(cell("td", value));
          const source = cell("td", r.source_locator), url = safeExternalURL(r.source_url);
          if (url) {
            const link = cell("a", "Mở nguồn được khai báo");
            link.href = url;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            source.append(document.createElement("br"), link);
          } else {
            const reference = cell("small", r.source_url);
            reference.style.overflowWrap = "anywhere";
            source.append(document.createElement("br"), reference);
          }
          row2.append(source);
          body2.append(row2);
        }
        table2.append(body2);
        observationWrap.append(table2);
      } catch (error) {
        if (req.isCurrent()) observationStatus.textContent = error.message;
      }
    }
    select.addEventListener("change", loadPoint);
    await loadPoint();
  } catch (error) {
    status.className = "notice error";
    status.textContent = error.message;
  }
}
