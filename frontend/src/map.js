import Map from 'ol/Map.js';
import View from 'ol/View.js';
import GeoJSON from 'ol/format/GeoJSON.js';
import TileLayer from 'ol/layer/Tile.js';
import VectorLayer from 'ol/layer/Vector.js';
import OSM from 'ol/source/OSM.js';
import VectorSource from 'ol/source/Vector.js';
import { Circle as CircleStyle, Fill, Stroke, Style, Text } from 'ol/style.js';
import { defaults as defaultControls, ScaleLine } from 'ol/control.js';
import { fromLonLat } from 'ol/proj.js';

export function hasCoordinates(feature) {
  const g = feature.geometry;
  return g?.type === 'Point' && Array.isArray(g.coordinates) && g.coordinates.length >= 2 &&
    Number.isFinite(g.coordinates[0]) && Number.isFinite(g.coordinates[1]) &&
    Math.abs(g.coordinates[0]) <= 180 && Math.abs(g.coordinates[1]) <= 90;
}

export function createStationMap(target, { onSelect, onTileError }) {
  let selectedCode = null;
  const source = new VectorSource({ wrapX: false });
  const background = new OSM({ url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', maxZoom: 19 });
  const baseLayer = new TileLayer({ source: background, preload: 0 });
  const styleCache = new globalThis.Map();
  const layer = new VectorLayer({
    source,
    style(feature) {
      const selected = feature.get('site_code') === selectedCode;
      const key = `${feature.get('site_code')}:${selected}`;
      if (!styleCache.has(key)) styleCache.set(key, new Style({
        image: new CircleStyle({
          radius: selected ? 10 : 7,
          fill: new Fill({ color: selected ? '#087f78' : '#ffffff' }),
          stroke: new Stroke({ color: selected ? '#ffffff' : '#087f78', width: 3 }),
        }),
        text: new Text({
          text: feature.get('site_name'), offsetY: -24,
          font: `${selected ? 700 : 600} 13px "Segoe UI", sans-serif`,
          fill: new Fill({ color: '#14333d' }), stroke: new Stroke({ color: '#ffffff', width: 4 }),
        }),
        zIndex: selected ? 2 : 1,
      }));
      return styleCache.get(key);
    },
  });
  const map = new Map({
    target, layers: [baseLayer, layer],
    view: new View({ center: fromLonLat([105.8, 10.55]), zoom: 8, minZoom: 3, maxZoom: 18, enableRotation: false }),
    controls: defaultControls({ attributionOptions: { collapsible: false }, rotate: false }).extend([
      new ScaleLine({ units: 'metric' }),
    ]),
  });
  background.on('tileloaderror', () => onTileError());
  map.on('singleclick', event => {
    const feature = map.forEachFeatureAtPixel(event.pixel, item => item, { hitTolerance: 8, layerFilter: item => item === layer });
    if (feature) onSelect(feature.get('site_code'));
  });
  map.on('pointermove', event => {
    map.getTargetElement().style.cursor = map.hasFeatureAtPixel(event.pixel, { hitTolerance: 8, layerFilter: item => item === layer }) ? 'pointer' : '';
  });
  const observer = new ResizeObserver(() => map.updateSize());
  observer.observe(target);
  const fit = () => {
    if (source.getFeatures().length) map.getView().fit(source.getExtent(), {
      padding: [62, 75, 62, 75], maxZoom: 11, duration: 250,
    });
  };
  return {
    setStations(collection) {
      source.clear(); styleCache.clear();
      const valid = collection.features.filter(hasCoordinates);
      source.addFeatures(new GeoJSON().readFeatures({ type: 'FeatureCollection', features: valid }, {
        dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857',
      }));
      fit();
      return valid.length;
    },
    select(code) { selectedCode = code; layer.changed(); },
    fit,
    setBasemapVisible(visible) { baseLayer.setVisible(visible); },
    destroy() { observer.disconnect(); map.setTarget(undefined); },
  };
}
