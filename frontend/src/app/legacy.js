const aliases = { "#forecast": "#forecasts", "#future-forecast": "#forecasts", "#intake": "#data-quality", "#mapSection": "#observations", "#historySection": "#observations", "#mainContent": "#overview" };
location.replace("/workspace.html" + (aliases[location.hash] || location.hash || "#overview"));
