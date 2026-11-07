"""Serve persisted multivariate models with explicit input dates and provenance."""
import calendar
from datetime import date, datetime
import math
from uuid import uuid4

from backend.domain import multivariate_ec as models
from backend.repositories import multivariate_inputs as weather
from backend.repositories import hydrology_inputs as hydrology
from backend.schemas import LOCAL_TZ
from backend.services.workspace import WorkspaceError


def _target(value):
    try:
        result = datetime.strptime(value, '%Y-%m').date()
        if result.strftime('%Y-%m') != value:
            raise ValueError()
        return result
    except (TypeError, ValueError) as exc:
        raise WorkspaceError(422, 'Tháng dự báo phải có dạng YYYY-MM.') from exc


def _catalog():
    try:
        return models.model_catalog()
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        raise WorkspaceError(503, 'Chưa đọc được mô hình đa biến. Chạy scripts/train_multivariate_ec.py bằng môi trường mô hình của dự án.') from exc


def _station(station):
    try:
        key = models.normalize_station(station)
    except (ValueError, AttributeError) as exc:
        raise WorkspaceError(404, 'Trạm này chưa có mô hình dự báo đa biến.') from exc
    return next((item for item in _catalog() if models.normalize_station(item['station']) == key), None)


def catalog():
    items = _catalog()
    now = datetime.now(LOCAL_TZ)
    next_month = date(now.year + (now.month == 12), now.month % 12 + 1, 1)
    return dict(status='AVAILABLE', stations=items,
                model_version=', '.join(sorted({item['model_version'] for item in items})),
                default_target_month=next_month.strftime('%Y-%m'), unit='mS/m',
                weather_lag_months=2,
                input_note='Mưa, nhiệt độ và gió của tháng t−2, cộng chu kỳ tháng. Mỹ Tho dùng thêm lưu lượng Kratie và mực nước Tân Châu tháng t−2; các trạm khác giữ mô hình riêng.')


def evaluation(station: str, protocol='HISTORICAL', experiment=None, ec_delay_days=5):
    try:
        if protocol == 'FROZEN_EC_WEATHER_ONLY_V1':
            from backend.domain.ec_gap_evaluation import records
            return records(station, experiment, ec_delay_days)
        return models.evaluation_records(station)
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        raise WorkspaceError(503, 'Chưa đọc được kết quả đánh giá của mô hình đa biến này.') from exc


def inputs(station: str, target_month: str):
    target = _target(target_month)
    selected = _station(station)
    if selected is None:
        raise WorkspaceError(404, 'Chưa đăng ký mô hình cho trạm này.')
    hydro = None
    if models.normalize_station(selected['station']) == 'MYTHO':
        try:
            hydro = hydrology.get_hydrology_input(target_month)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise WorkspaceError(422, 'Chưa đủ lưu lượng Kratie hoặc mực nước Tân Châu tháng t−2 để dự báo Mỹ Tho. Cần cập nhật nguồn thủy văn đầy đủ.') from exc
    try:
        result = weather.get_weather_input(selected['station'], target_month)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        if hydro is not None:
            return dict(station=selected['station'], target_month=target_month,
                input_month=_input_month(target), complete=False, wind_unit='m/s',
                source='WEATHER_UNAVAILABLE', hydrology=hydro,
                availability_note='Chưa có đủ khí tượng lưu trữ; có thể nhập khí tượng thủ công.')
        raise WorkspaceError(422, 'Chưa có đủ khí tượng đúng đơn vị cho tháng đầu vào. Cập nhật bằng scripts/update_multivariate_weather.py hoặc chọn đầu vào do người dùng cung cấp.') from exc
    if result.get('wind_unit') != 'm/s' or result.get('complete') is not True:
        raise WorkspaceError(422, 'Khí tượng chưa đủ ngày hoặc chưa xác nhận đơn vị gió m/s để chạy mô hình này.')
    try:
        expected_month = _input_month(target)
        expected_date = date.fromisoformat(expected_month + '-01')
        month_end = expected_date.replace(day=calendar.monthrange(expected_date.year, expected_date.month)[1])
        if (result['input_month'] != expected_month
                or models.normalize_station(result['station']) != models.normalize_station(selected['station'])
                or result['observed_through'] != month_end.isoformat()):
            raise ValueError('Weather input station/month mismatch.')
        available = datetime.fromisoformat(result['assumed_available_at'])
        if available.tzinfo is None and len(result['assumed_available_at']) == 10:
            available = available.replace(hour=23, minute=59, second=59, tzinfo=LOCAL_TZ)
        if (available.tzinfo is None or available > datetime.now(LOCAL_TZ)
                or available.astimezone(LOCAL_TZ).date() < month_end):
            raise ValueError('Future or timezone-free availability.')
    except (KeyError, ValueError, TypeError) as exc:
        raise WorkspaceError(422, 'Kỳ khí tượng này chưa đủ điều kiện sẵn có tại thời điểm phát hành.') from exc
    return dict(result, station=selected['station'], target_month=target_month,
                assumed_available_at=available.isoformat(), hydrology=hydro)


def predict(payload):
    station, target_month = payload['station'], payload['target_month']
    target = _target(target_month)
    selected = _station(station)
    if selected is None:
        raise WorkspaceError(404, 'Chưa đăng ký mô hình cho trạm này.')
    if target_month <= selected['trained_through'][:7]:
        raise WorkspaceError(422, 'Chọn tháng sau kỳ huấn luyện ' + selected['trained_through'][:7] + ' để tránh dùng mô hình đã học nhãn của tháng cần dự báo.')
    mode = payload['input_mode']
    if mode == 'ARCHIVE':
        source = inputs(selected['station'], target_month)
        if source.get('complete') is not True:
            raise WorkspaceError(422, 'Chưa đủ khí tượng lưu trữ; chọn đầu vào khí tượng do người dùng cung cấp.')
        values = {key: source[key] for key in models.WEATHER_AGG}
        hydro = source.get('hydrology')
    else:
        values = {key: payload.get(key) for key in models.WEATHER_AGG}
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values.values()):
            raise WorkspaceError(422, 'Cần điền đủ ba đầu vào khí tượng hữu hạn.')
        source = dict(source='USER_PROVIDED', input_month=_input_month(target), wind_unit='m/s',
                      observed_through=None, assumed_available_at=None, sha256=None, complete=True)
        hydro = None
        if models.normalize_station(selected['station']) == 'MYTHO':
            try:
                hydro = hydrology.get_hydrology_input(target_month)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise WorkspaceError(422, 'Mỹ Tho cần đủ lưu lượng Kratie và mực nước Tân Châu tháng t−2 kể cả khi nhập khí tượng thủ công.') from exc
    if hydro:
        values.update({key: hydro[key] for key in models.HYDRO_FEATURES})
    try:
        prediction = models.predict_month(selected['station'], target.isoformat(), values)
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        raise WorkspaceError(503, 'Không chạy được mô hình đa biến. Kiểm tra artifact và phiên bản thư viện đã huấn luyện.') from exc
    if (prediction['model_version'] != selected['model_version']
            or prediction['training_cutoff'] != selected['trained_through']):
        raise WorkspaceError(503, 'Mô hình vừa thay đổi; tải lại danh mục và chạy lại dự báo để giữ đúng nguồn.')
    now = datetime.now(LOCAL_TZ)
    raw_features = prediction['feature_values']
    features = [dict(name=key, label=models.LABELS[key], value=value, unit=models.UNITS[key],
                     source='CALENDAR' if key.startswith('month_') else
                            hydro['source'] if key in models.HYDRO_FEATURES and hydro else source['source'])
                for key, value in raw_features.items()]
    return dict(prediction, prediction_id=str(uuid4()), site_code=selected['site_code'],
                target_month=target_month, input_month=source['input_month'], input_mode=mode,
                issued_at=now.isoformat(), inputs=features, input_provenance=source,
                hydrology_provenance=hydro,
                training=dict(through=selected['trained_through'], samples=selected['training_samples']),
                metrics=selected['metrics'], evaluation=selected['evaluation'],
                gap_validation=selected.get('gap_validation'),
                feature_importance=selected['feature_importance'],
                data_kind='MULTIVARIATE_MONTHLY_FORECAST',
                target_is_before_current_month=target < now.date().replace(day=1),
                conditional_on_user_inputs=mode == 'MANUAL',
                note='Dự báo tính trực tiếp từ mô hình đã huấn luyện. Sai số lịch sử giữ riêng với dự báo mới; EC chưa quy đổi thành độ mặn.')


def _input_month(target):
    index = target.year * 12 + target.month - 1 - 2
    return f'{index // 12:04d}-{index % 12 + 1:02d}'
