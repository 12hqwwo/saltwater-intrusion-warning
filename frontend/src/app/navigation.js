import { getCurrentRole } from '../auth/auth-service.js';
import { applyRoleVisibility } from '../auth/role-visibility.js';

export function bindNavigation(canViewSection = () => true) {
  const aliases = { forecast: "forecasts", "future-forecast": "forecasts", intake: "data-quality", main: "overview" };
  const views = new Set(["overview", "observations", "forecasts", "data-quality", "gates"]);
  function navigate() {
    const hash = location.hash.slice(1), requested = aliases[hash] || (views.has(hash) ? hash : "overview");
    const view = canViewSection(requested) ? requested : 'observations';
    if (view !== requested) location.hash = '#observations';
    applyRoleVisibility(getCurrentRole());
    for (const panel of document.querySelectorAll("[data-view]")) {
      const allowed = !panel.dataset.visibleForRoles || panel.dataset.visibleForRoles.split(/\s+/).includes(getCurrentRole());
      panel.hidden = panel.dataset.view !== view || !allowed;
    }
    for (const link of document.querySelectorAll("nav a")) {
      if (link.hash === "#" + view) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    }
    document.title = `WebGIS Đồng Tháp · ${document.querySelector("nav a[aria-current]")?.textContent || "Tổng quan"}`;
    window.dispatchEvent(new CustomEvent("workspace:viewchange", { detail: { view } }));
    document.getElementById(view)?.scrollIntoView({ block: 'start' });
  }
  window.addEventListener("hashchange", navigate);
  window.addEventListener('workspace:auth-changed', navigate);
  navigate();
}
