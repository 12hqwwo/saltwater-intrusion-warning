import { createRequestGate } from "./api.js";
import { workspaceAPI as requestJSON } from "./shared/workspace-api.js";

const cell = (tag, value) => {
  const element = document.createElement(tag);
  element.textContent = value;
  return element;
};

function detail(summary, ...contents) {
  const wrapper = document.createElement("details");
  wrapper.className = "intake-detail";
  wrapper.append(cell("summary", summary), ...contents);
  return wrapper;
}

function table(headers, rows) {
  const wrap = document.createElement("div");
  wrap.className = "table-wrap";
  const element = document.createElement("table");
  const head = document.createElement("thead");
  const heading = document.createElement("tr");
  headers.forEach(label => heading.append(cell("th", label)));
  head.append(heading);
  const body = document.createElement("tbody");
  for (const values of rows) {
    const row = document.createElement("tr");
    values.forEach(value => row.append(cell("td", value ?? "—")));
    body.append(row);
  }
  element.append(head, body);
  wrap.append(element);
  return wrap;
}

export async function showIntake(host = document.getElementById("intakeHost")) {
  const section = document.createElement("section");
  section.id = "intake";
  section.className = "section panel intake-panel";
  const status = cell("p", "Đang đọc hồ sơ dữ liệu…");
  status.setAttribute("role", "status");
  section.append(status);
  host.replaceChildren(section);
  try {
    const [audit, coverage, catalogue] = await Promise.all([
      requestJSON("/intake"),
      requestJSON("/intake/coverage"),
      requestJSON("/intake/measurement-points")
    ]);
    status.className = "intake-status";
    status.textContent = "Hồ sơ đang rà soát · Chưa xác minh chất lượng";
    section.append(cell("p", "Các số đo mới được giữ riêng để kiểm tra nguồn và vị trí đo. Chúng chưa được đưa vào chuỗi quan trắc EC hoặc dữ liệu huấn luyện."));

    const counts = audit.counts;
    const summary = document.createElement("div");
    summary.className = "intake-summary";
    for (const [value, label] of [
      [counts.csv_rows, "dòng trong tệp nguồn"],
      [counts.station_count, "trạm có dữ liệu"],
      [catalogue.counts.records, "giá trị giữ để rà soát"]
    ]) {
      const item = document.createElement("div");
      item.append(cell("strong", new Intl.NumberFormat("vi-VN").format(value ?? 0)), cell("span", label));
      summary.append(item);
    }
    section.append(summary);

    const explanation = document.createElement("div");
    explanation.className = "intake-explanation";
    explanation.append(cell("h3", "Cần kiểm tra gì?"));
    const points = document.createElement("ul");
    points.append(
      cell("li", "Xác nhận điểm đo thuộc sông hay nội đồng trước khi đối chiếu."),
      cell("li", "Kiểm tra ngày và kỳ đo; số đo cùng ngày không phải dự báo ngày hôm sau."),
      cell("li", "Chỉ dùng số đo đã qua kiểm tra chất lượng cho kết luận tại nơi sử dụng.")
    );
    explanation.append(points);
    section.append(explanation);

    const coverageRows = coverage.items.map(row => [row.station, row.first, row.last, row.unique_dates, row.longest_daily_run, row.next1d_labels]);
    section.append(detail("Xem khoảng thời gian và số ngày có dữ liệu", table(
      ["Trạm", "Từ", "Đến", "Ngày có mẫu", "Chuỗi liên tục dài nhất", "Mẫu ngày tiếp theo"], coverageRows
    )));

    const review = document.createElement("div");
    review.className = "intake-review";
    review.append(cell("p", `${catalogue.counts.records} giá trị được giữ nguyên; ${catalogue.counts.rejected} ô không đủ điều kiện chuẩn hóa được ghi lại để rà soát. Ô trống không được tính là 0.`));
    const label = cell("label", "Điểm đo");
    const select = document.createElement("select");
    const positionLabels = { RIVER_REPORTED: "Trên sông", INTERIOR_0M: "Nội đồng · tại cống/cầu", INTERIOR_200M: "Nội đồng · cách 200 m" };
    for (const point of catalogue.items) {
      const option = cell("option", `${point.name} · ${positionLabels[point.position] || point.position} · ${point.records} mẫu`);
      option.value = point.key;
      select.append(option);
    }
    label.append(select);
    const observationStatus = cell("p", "");
    observationStatus.setAttribute("role", "status");
    const observationWrap = document.createElement("div");
    review.append(label, observationStatus, observationWrap);
    const measurementDetail = detail("Tra cứu số đo độ mặn chưa xác minh", review);
    section.append(measurementDetail);

    const requests = createRequestGate();
    async function loadPoint() {
      const req = requests.next();
      observationWrap.replaceChildren();
      observationStatus.textContent = "Đang đọc số đo…";
      try {
        const data = await requestJSON("/intake/observations?point=" + encodeURIComponent(select.value), req);
        if (!req.isCurrent()) return;
        observationStatus.textContent = `${data.items.length}/${data.total} mẫu · đơn vị g/L · chưa xác minh chất lượng.`;
        observationWrap.append(table(
          ["Ngày trong nguồn", "Giờ / kỳ đo", "Cách đo", "Độ mặn (g/L)"],
          data.items.map(row => [row.observed_date, row.source_time_or_period, row.measurement_regime, row.value])
        ));
      } catch (error) {
        if (req.isCurrent()) observationStatus.textContent = error.message;
      }
    }
    measurementDetail.addEventListener("toggle", () => {
      if (measurementDetail.open && !observationWrap.childElementCount) loadPoint();
    });
    select.addEventListener("change", loadPoint);

    const auditDetails = document.createElement("div");
    auditDetails.className = "intake-audit";
    auditDetails.append(
      cell("p", audit.note),
      cell("p", `${audit.issues.CALENDAR_MISMATCH_feat_salinity_lag1_g_l || 0} dòng có giá trị ngày trước chưa khớp; ${audit.issues.TARGET_REQUIRES_MEASUREMENT_LOCATION_DISAMBIGUATION || 0} dòng cần xác định rõ vị trí đo.`),
      cell("p", `${counts.next1d_label_count} dòng có nhãn ngày tiếp theo; ${counts.full_hydromet_next1d} dòng có đủ nhãn, triều, mực nước kênh và mưa.`)
    );
    section.append(detail("Chi tiết kiểm tra nguồn", auditDetails));
  } catch (error) {
    status.className = "notice error";
    status.textContent = error.message;
  }
}
