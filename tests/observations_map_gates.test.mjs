import assert from 'node:assert/strict';
import test from 'node:test';
import GeoJSON from '../frontend/node_modules/ol/format/GeoJSON.js';
import VectorSource from '../frontend/node_modules/ol/source/Vector.js';
import { databaseGateFeatureCollection } from '../frontend/src/features/observations-map.js';

test('database gates keep GeoJSON geometry separate from display properties', () => {
  const rows = [{
    gate_code: 'DTG001', gate_name: 'Cống Vàm Giồng',
    geometry: { type: 'Point', coordinates: [106.547889, 10.302] },
  }];
  const collection = databaseGateFeatureCollection(rows);
  assert.equal(collection.features.length, 1);
  assert.equal(Object.hasOwn(collection.features[0].properties, 'geometry'), false);
  assert.deepEqual(collection.features[0].geometry, rows[0].geometry);

  const features = new GeoJSON().readFeatures(collection, {
    dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857',
  });
  const source = new VectorSource();
  source.addFeatures(features);
  assert.equal(typeof features[0].getGeometry().getExtent, 'function');
  assert.equal(source.getFeatures().length, 1);
});
