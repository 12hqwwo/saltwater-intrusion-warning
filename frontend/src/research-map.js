import Map from 'ol/Map.js';
import View from 'ol/View.js';
import GeoJSON from 'ol/format/GeoJSON.js';
import TileLayer from 'ol/layer/Tile.js';
import VectorLayer from 'ol/layer/Vector.js';
import OSM from 'ol/source/OSM.js';
import VectorSource from 'ol/source/Vector.js';
import { Circle, Fill, Stroke, Style, Text, RegularShape } from 'ol/style.js';
import { fromLonLat } from 'ol/proj.js';
import { defaults as controls, ScaleLine } from 'ol/control.js';
import { mapFeatures } from './research-utils.js';

export function createResearchMap(target, { onSelect, onTileError }) {
  const source = new VectorSource(), boundarySource = new VectorSource(), gateSource = new VectorSource();
  const osm = new OSM(), base = new TileLayer({ source: osm });
  let selected = null, collection = { type: 'FeatureCollection', features: [] }, showUnconfirmed = false;
  const formatter = new GeoJSON(), cache = new globalThis.Map();
  const options = { dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857' };
  const boundaries = new VectorLayer({ source: boundarySource, style: new Style({ stroke: new Stroke({ color: '#578781', width: 1.5 }), fill: new Fill({ color: 'rgba(166,206,182,.23)' }) }) });
  const stations = new VectorLayer({ source, declutter: true, style(f) {
    const key = `${f.get('site_code')}:${f.get('site_code') === selected}:${f.get('assumed_crs')}`;
    if (!cache.has(key)) {
      const active = f.get('site_code') === selected, color = f.get('assumed_crs') ? '#b77a23' : '#097c78';
      cache.set(key, new Style({
        image: new Circle({ radius: active ? 9 : 6, fill: new Fill({ color: active ? color : '#fff' }), stroke: new Stroke({ color, width: 2.5, lineDash: f.get('assumed_crs') ? [3, 2] : undefined }) }),
        text: new Text({ text: f.get('site_name'), offsetY: -18, font: '600 12px Segoe UI', fill: new Fill({ color: '#173c43' }), stroke: new Stroke({ color: '#fff', width: 4 }) }), zIndex: active ? 9 : 1,
      }));
    }
    return cache.get(key);
  } });
  const gates = new VectorLayer({ source: gateSource, style: new Style({ image: new RegularShape({ points: 4, radius: 8, angle: 0, fill: new Fill({ color: '#7560a7' }), stroke: new Stroke({ color: '#fff', width: 2 }) }) }) });
  const map = new Map({ target, layers: [base, boundaries, gates, stations], controls: controls({ rotate: false, attributionOptions: { collapsible: false } }).extend([new ScaleLine()]),
    view: new View({ center: fromLonLat([105.8, 10.45]), zoom: 8.7, minZoom: 5, maxZoom: 18, enableRotation: false }) });
  osm.on('tileloaderror', onTileError);
  map.on('singleclick', event => { const f = map.forEachFeatureAtPixel(event.pixel, f => f, { layerFilter: l => l === stations, hitTolerance: 7 }); if (f) onSelect(f.get('site_code')); });
  const observer = new ResizeObserver(() => map.updateSize()); observer.observe(target);
  const update = () => { source.clear(); cache.clear(); source.addFeatures(formatter.readFeatures(mapFeatures(collection, showUnconfirmed), options)); return source.getFeatures().length; };
  return {
    setStations(value) { collection = value; return update(); },
    setUnconfirmed(value) { showUnconfirmed = value; return update(); },
    setBoundaries(value) { boundarySource.clear(); boundarySource.addFeatures(formatter.readFeatures(value, options)); },
    setGates(items) { gateSource.clear(); gateSource.addFeatures(formatter.readFeatures({ type: 'FeatureCollection', features: items.filter(r => r.geometry).map(r => ({ type: 'Feature', geometry: r.geometry, properties: r })) }, options)); },
    select(code) { selected = code; stations.changed(); },
    fit() { const extent = boundarySource.getFeatures().length ? boundarySource.getExtent() : source.getExtent(); if (extent.every(Number.isFinite)) map.getView().fit(extent, { padding: [30, 35, 30, 35], maxZoom: 10, duration: 200 }); },
    setBase(value) { base.setVisible(value); },
    destroy() { observer.disconnect(); map.setTarget(undefined); },
  };
}
