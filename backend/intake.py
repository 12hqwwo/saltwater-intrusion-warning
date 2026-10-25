"""Read-only intake audit, separate from accepted observation and forecast APIs."""
import hashlib
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query

ROOT = Path(__file__).resolve().parents[1]
INTAKE = ROOT / 'data/external/user_v3_review_20261015'
router = APIRouter(prefix='/intake', tags=['Data intake'])


def read_intake():
    try:
        audit = json.loads((INTAKE / 'audit.json').read_text(encoding='utf-8'))
        for record in audit['files']:
            path = INTAKE / record['file']
            if path.resolve().parent != INTAKE.resolve():
                raise ValueError('Invalid intake file name')
            if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
                raise ValueError('Original checksum mismatch')
        return audit
    except (OSError, ValueError, KeyError) as exc:
        raise HTTPException(503, 'Không đọc được hồ sơ tiếp nhận hoặc checksum không khớp. Không dùng dữ liệu thay thế.') from exc


@router.get('')
def summary():
    audit = read_intake()
    return dict(storage_mode='review_files', status='UNVERIFIED',
                training_eligible=False, gate_decision_eligible=False,
                imported_observations=0,
                files=[{k: r[k] for k in ('file','sha256','received_at','status')} for r in audit['files']],
                counts={k: audit[k] for k in ('csv_rows','station_count','next1d_label_count','full_hydromet_next1d','spatial_features','spatial_classes')},
                issues=audit['issue_counts'],
                note='Số đếm ô có dữ liệu, chưa phải số mẫu đã xác minh. Hồ sơ tiếp nhận đọc từ tệp, độc lập với chế độ lưu quan trắc.')


@router.get('/coverage')
def coverage():
    read_intake()
    try:
        items = json.loads((INTAKE / 'station_coverage.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise HTTPException(503, 'Chưa đọc được kiểm toán độ phủ.') from exc
    return dict(items=items, training_eligible=False)


def read_normalized():
    audit = read_intake()
    try:
        raw = (INTAKE/'normalized_review.json').read_bytes()
        manifest = json.loads((INTAKE/'normalized_review.manifest.json').read_text(encoding='utf-8'))
        if hashlib.sha256(raw).hexdigest() != manifest['sha256']:
            raise ValueError('Normalized checksum mismatch')
        workbook_sha = next(r['sha256'] for r in audit['files'] if r['file'].endswith('.xlsx'))
        if manifest['source_sha256'] != workbook_sha:
            raise ValueError('Normalized rows belong to a different workbook')
        data = json.loads(raw)
        if data['status'] != 'REVIEW_ONLY' or any(r['training_eligible'] or r['gate_decision_eligible'] or r['workbook_sha256'] != workbook_sha for r in data['records']):
            raise ValueError('Intake cannot authorize observations')
        return data
    except (OSError, ValueError, KeyError, StopIteration) as exc:
        raise HTTPException(503, 'Chưa có bảng chuẩn hóa hợp lệ. Không tự thay bằng dữ liệu mẫu.') from exc


@router.get('/measurement-points')
def points():
    data=read_normalized()
    catalogue={}
    for r in data['records']:
        key=r['measurement_point_key']
        catalogue.setdefault(key,dict(key=key,name=r['source_station_name'],position=r['position'],records=0))['records'] += 1
    return dict(items=sorted(catalogue.values(),key=lambda r:r['key']),counts=data['counts'],status='REVIEW_ONLY')


@router.get('/observations')
def observations(point: str = Query(min_length=1,max_length=150), offset: int = Query(0,ge=0), limit: int = Query(100,ge=1,le=200)):
    data=read_normalized()
    selected=sorted([r for r in data['records'] if r['measurement_point_key']==point],key=lambda r:(r['observed_date'],r['record_id']))
    if not selected:
        raise HTTPException(404,'Không tìm thấy điểm đo trong hồ sơ tiếp nhận.')
    return dict(items=selected[offset:offset+limit],total=len(selected),offset=offset,limit=limit,status='REVIEW_ONLY')
