/**
 * Data boundary for the Pilot Gò Công WebGIS.
 *
 * UI code consumes named domain methods instead of file paths or database
 * details.  A later PostGIS-backed API can preserve these method contracts.
 */
export class PilotSpatialDataService {
  constructor(baseUrl = '/pilot/spatial', fetcher = window.fetch.bind(window)) {
    this.baseUrl = baseUrl;
    this.fetcher = fetcher;
  }

  async request(path) {
    const response = await this.fetcher(this.baseUrl + path, {
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
    return response.json();
  }

  waterways() { return this.request('/waterways'); }
  routes() { return this.request('/routes'); }
  crossings() { return this.request('/crossings'); }
  coordinateCandidates() { return this.request('/coordinate-candidates'); }
  sites() { return this.request('/sites'); }
  metrics() { return this.request('/metrics'); }

  async loadMapBundle() {
    const [waterways, routes, crossings, candidates, sites, metrics] = await Promise.all([
      this.waterways(),
      this.routes(),
      this.crossings(),
      this.coordinateCandidates(),
      this.sites(),
      this.metrics(),
    ]);
    return { waterways, routes, crossings, candidates, sites, metrics };
  }
}

export const pilotSpatialDataService = new PilotSpatialDataService();
