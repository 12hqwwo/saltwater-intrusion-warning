/** User-defined comparison settings shared by the map and EC charts. */
const key = "workspace.ec-comparison.v1";
let current = null;
try {
  const saved = JSON.parse(localStorage.getItem(key) || "null");
  if (saved && Number.isFinite(saved.threshold) && saved.threshold > 0) current = saved;
} catch { /* The workspace also runs when browser storage is unavailable. */ }

export function ecComparison() { return current; }

export function setECComparison(value) {
  if (value && (!Number.isFinite(value.threshold) || value.threshold <= 0)) {
    throw new Error("Ngưỡng EC phải là số lớn hơn 0 mS/m.");
  }
  current = value ? { threshold: value.threshold, purpose: String(value.purpose || "Ngưỡng tự nhập"), reference: String(value.reference || "Chưa ghi nguồn") } : null;
  try {
    if (current) localStorage.setItem(key, JSON.stringify(current));
    else localStorage.removeItem(key);
  } catch { /* Changes remain available for the current session. */ }
  window.dispatchEvent(new CustomEvent("workspace:ec-comparison", { detail: current }));
}

export function comparisonLines() {
  return current ? [{ value: current.threshold, label: `${current.purpose}: ${current.threshold} mS/m`, color: "#bc6430" }] : [];
}
