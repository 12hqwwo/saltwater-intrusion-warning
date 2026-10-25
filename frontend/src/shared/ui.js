import { safeExternalURL } from "../research-utils.js";

export const $ = (id) => document.getElementById(id);
export const num = (v) => Number.isFinite(v) ? new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 3 }).format(v) : "—";
export const node = (tag, text, cls) => {
  const n = document.createElement(tag);
  if (text !== undefined) n.textContent = text;
  if (cls) n.className = cls;
  return n;
};
export function save(name, value, type = "application/json") {
  const content = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = node("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function sourceAnchor(source, text) {
  const a = node("a", text);
  const url = safeExternalURL(source?.article_url || source?.url);
  if (url) {
    a.href = url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
  } else a.textContent = text;
  return a;
}
export function saveCSV(name, rows, keys) {
  const quote = (value) => '"' + String(value ?? "").replace(/^[=+@-]/, "'$&").replaceAll('"', '""') + '"';
  const lines = [keys.join(",")];
  for (const row of rows) {
    lines.push(keys.map(key => quote(row[key])).join(","));
  }
  save(name, "\uFEFF" + lines.join("\r\n"), "text/csv;charset=utf-8");
}
