const aliases = { "#forecast": "#forecasts", "#future-forecast": "#forecasts", "#intake": "#data-quality" };
location.replace("/workspace.html" + (aliases[location.hash] || location.hash || "#overview"));
