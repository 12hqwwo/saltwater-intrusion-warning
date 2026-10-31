export function bindNavigation() {
  const aliases = { forecast: "forecasts", "future-forecast": "forecasts", intake: "data-quality", main: "overview" };
  const views = new Set(["overview", "observations", "forecasts", "data-quality", "gates"]);
  function navigate() {
    const hash = location.hash.slice(1), view = aliases[hash] || (views.has(hash) ? hash : "overview");
    for (const panel of document.querySelectorAll("[data-view]")) panel.hidden = panel.dataset.view !== view;
    for (const link of document.querySelectorAll("nav a")) {
      if (link.hash === "#" + view) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    }
    document.title = `WebGIS Đồng Tháp · ${document.querySelector("nav a[aria-current]")?.textContent || "Tổng quan"}`;
    window.dispatchEvent(new CustomEvent("workspace:viewchange", { detail: { view } }));
    // Reveal the newly selected panel before scrolling to its hash target.
    // Native fragment scrolling may otherwise run while that panel is hidden.
    document.getElementById(view)?.scrollIntoView({ block: 'start' });
  }
  window.addEventListener("hashchange", navigate);
  navigate();
}
