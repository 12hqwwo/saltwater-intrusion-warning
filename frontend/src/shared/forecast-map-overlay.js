import { validEc, validMonth, validPrediction } from './forecast-contract.js';
import { interpolateStationEc, MY_THUAN_RATIO, THREE_STATION_MODE, TWO_STATION_MODE } from './river-interpolation.js';

export const DEFAULT_P90_MYTHO_MS_M = 60.42;
export const EC_TO_SALINITY_GL_FACTOR = 0.0064;
export const DIRECT_FORECAST_MODEL = 'MULTIVARIATE_RF_5';
export const COMPACT_FORECAST_MODEL = 'RF_compact';
export const DIRECT_FORECAST_SUBTITLE = 'Mỹ Tho: RF 300 cây với khí tượng, lưu lượng Kratie và mực nước Tân Châu tháng t−2. Mỹ Thuận và Tân Châu: mô hình khí tượng riêng.';
export const COMPACT_FORECAST_SUBTITLE = 'Thí nghiệm RF_compact lưu trữ sau mẫu EC cuối; không phải mô hình chính hiện tại.';
export const FORECAST_SPATIAL_DISCLAIMER = 'Lớp nội suy hình học dọc trục sông phục vụ sàng lọc không gian';

export function forecastModelLabel(sourceModel) {
  return sourceModel === DIRECT_FORECAST_MODEL ? 'Dự báo đa biến theo trạm' : 'RF_compact 8 biến';
}

export function normalizeForecastContext(context) {
  if (!context || ![DIRECT_FORECAST_MODEL, COMPACT_FORECAST_MODEL].includes(context.sourceModel) ||
      !validMonth(context.targetMonth) || !validEc(context.mythoEc) || !validEc(context.tanchauEc)) {
    throw new Error('Kịch bản bản đồ cần tháng hợp lệ và EC không âm tại Mỹ Tho, Tân Châu.');
  }
  const p90Threshold = context.p90Threshold ?? DEFAULT_P90_MYTHO_MS_M;
  if (!validEc(p90Threshold)) throw new Error('Ngưỡng P90 phải là số hữu hạn không âm.');
  const historicalMissing = context.targetMonth < '2024-01' && context.mythuanEc === null && context.interpolationMode === TWO_STATION_MODE;
  if (!validEc(context.mythuanEc) && !historicalMissing) throw new Error('Cần dự báo Mỹ Thuận cho cùng tháng để nội suy ba trạm.');
  return { ...context, interpolationMode: historicalMissing ? TWO_STATION_MODE : THREE_STATION_MODE,
    p90Threshold, isHighVigilance: context.mythoEc >= p90Threshold };
}

/** Run the other station's model for the same target and scenario; never persist a second run. */
export async function loadMultivariateForecastContext(prediction, api, request = {}) {
  const codes = { TanChau: 'MRC_VN_019803', MyThuan: 'MRC_VN_019804', MyTho: 'MRC_VN_019805' };
  if (!validPrediction(prediction) || !codes[prediction.station] || prediction.site_code !== codes[prediction.station]) {
    throw new Error('Kết quả đa biến không hợp lệ để áp dụng lên sông.');
  }
  const others = await Promise.all(Object.keys(codes).filter(name => name !== prediction.station).map(async station => {
    const payload = { station, target_month: prediction.target_month, input_mode: prediction.input_mode };
    if (payload.input_mode === 'MANUAL') for (const name of ['rainfall_mm', 'temperature_degC', 'wind_source_units']) payload[name] = prediction.inputs.find(input => input.name === name).value;
    const result = await api('/multivariate/predict', { ...request, method: 'POST', body: payload, timeoutMs: 120_000 });
    if (!validPrediction(result, { ...payload, site_code: codes[station] })) throw new Error('Dự báo trạm còn lại không khớp tháng, kịch bản hoặc đơn vị EC.');
    return result;
  }));
  const values = Object.fromEntries([prediction, ...others].map(item => [item.station, item.predicted_ec_mS_m]));
  return normalizeForecastContext({
    sourceModel: DIRECT_FORECAST_MODEL, targetMonth: prediction.target_month,
    mythoEc: values.MyTho, tanchauEc: values.TanChau, mythuanEc: values.MyThuan,
    tanchauBasis: 'MODEL_PREDICTION', inputMode: prediction.input_mode,
  });
}

/** Clone API frames or GeoJSON fixtures; source geometry and evidence remain untouched. */
export function buildForecastOverlayFrame(baseFrame, forecastContext) {
  const key = Array.isArray(baseFrame?.river_segments) ? 'river_segments' : 'features';
  if (!baseFrame || !Array.isArray(baseFrame[key]) || !baseFrame[key].length) {
    throw new Error('Base frame không hợp lệ để dựng lớp phủ dự báo.');
  }
  const context = normalizeForecastContext(forecastContext);
  const frame = structuredClone(baseFrame);
  const features = frame[key];
  // The real corridor puts Mỹ Tho at km 125 and the estuary at km 175.
  // Keep the station anchor at its actual position; hold its EC beyond Mỹ Tho.
  const mythoKm = baseFrame.assumptions?.chainage_anchors_km?.[1];
  const anchored = Number.isFinite(mythoKm) && mythoKm > 0;
  const clamp = value => Math.max(0, Math.min(1, value));
  const ecAt = ratio => interpolateStationEc(ratio, context);
  features.forEach((feature, index) => {
    const props = feature.properties || {};
    const ratio = (name, kmName, fallback) => clamp(Number.isFinite(props[name]) ? props[name]
      : anchored && Number.isFinite(props[kmName]) ? props[kmName] / mythoKm : fallback);
    const start = ratio('axial_ratio_start', 'chainage_start_km', index / features.length);
    const end = ratio('axial_ratio_end', 'chainage_end_km', (index + 1) / features.length);
    const ec = ecAt((start + end) / 2), ecStart = ecAt(start), ecEnd = ecAt(end);
    feature.properties = { ...props,
      start_ec_mS_m: ecStart, end_ec_mS_m: ecEnd, ec_mS_m: ec,
      ec_stops: [0, ...(start < MY_THUAN_RATIO && MY_THUAN_RATIO < end && validEc(context.mythuanEc)
        ? [(MY_THUAN_RATIO - start) / (end - start)] : []), 1].map(fraction => ({ fraction, ec_mS_m: ecAt(start + (end - start) * fraction) })),
      interpolation_mode: context.interpolationMode,
      ec_start_ms_m: ecStart, ec_end_ms_m: ecEnd, ec_ms_m: ec,
      salinity_g_l: ec * EC_TO_SALINITY_GL_FACTOR,
      salinity_gl_est: Number((ec * EC_TO_SALINITY_GL_FACTOR).toFixed(4)),
      overlay_mode: 'MULTIVARIATE_FORECAST_OVERLAY',
      forecast_source_model: context.sourceModel, forecast_target_month: context.targetMonth,
    };
  });
  frame.overlayMetadata = { ...context, isForecastOverlay: true,
    baseMonth: baseFrame.year_month ?? null,
    interpolationBasis: context.interpolationMode,
    spatialDisclaimer: FORECAST_SPATIAL_DISCLAIMER,
    salinityConversion: 'Quy đổi tham khảo g/L = 0.0064 × EC (mS/m).',
  };
  frame.year_month = context.targetMonth;
  frame.interpolation_mode = context.interpolationMode;
  frame.interpolation_fallback_reason = context.interpolationMode === TWO_STATION_MODE ? 'MISSING_HISTORICAL_MYTHUAN_OBSERVATION' : null;
  // Gate assessment belongs to phase 2. Do not attach stale gate states/fronts to new EC.
  if (key === 'river_segments') {
    frame.gates = [];
    frame.isohaline_boundaries = [];
    frame.boundary_conditions = [];
    frame.inputs = { ...frame.inputs, year_month: context.targetMonth,
      tan_chau_ec_mS_m: context.tanchauEc, my_tho_ec_mS_m: context.mythoEc,
      my_thuan_ec_mS_m: context.mythuanEc, interpolation_mode: context.interpolationMode,
      tan_chau_salinity_g_l: context.tanchauEc * EC_TO_SALINITY_GL_FACTOR,
      my_tho_salinity_g_l: context.mythoEc * EC_TO_SALINITY_GL_FACTOR,
      data_regime: 'MULTIVARIATE_FORECAST_OVERLAY',
    };
  }
  return frame;
}

// Public context for the next phase; an event also lets consumers subscribe without polling.
export let activeForecastContext = null;

export function createForecastMapBridge({ onFrame, onContext, onError, eventTarget = globalThis.window } = {}) {
  let baseFrame = null, requestedContext = null;
  function publish(context) {
    activeForecastContext = context ? Object.freeze({ ...context }) : null;
    onContext?.(activeForecastContext);
    eventTarget?.dispatchEvent(new CustomEvent('workspace:active-forecast-context', { detail: activeForecastContext }));
  }
  function render() {
    if (!baseFrame || !requestedContext) {
      publish(null); onFrame?.(baseFrame); return null;
    }
    try {
      const context = normalizeForecastContext(requestedContext);
      const overlay = buildForecastOverlayFrame(baseFrame, context);
      onFrame?.(overlay); publish(context); return overlay;
    } catch (error) {
      requestedContext = null; publish(null); onFrame?.(baseFrame); onError?.(error); return null;
    }
  }
  return {
    setBaseFrame(frame) { baseFrame = frame; return render(); },
    apply(context) { requestedContext = { ...context }; return render(); },
    clear() { requestedContext = null; return render(); },
    getBaseFrame: () => baseFrame,
    getRequestedContext: () => requestedContext,
  };
}
