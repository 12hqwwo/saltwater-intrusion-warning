"""Explicit hypothetical hydraulic/EC screening, never an operating command."""
from backend.domain.gates import numeric, stamp, GateInputError


def simulate(policy, data):
    result = dict(schema_version=1, evaluation_mode='SIMULATION',
                  status='INSUFFICIENT_DATA', simulation_outcome=None,
                  recommendation=None, actuator_command=None, deployment_ready=False,
                  requires_operator_review=True, gate_code=data.get('gate_code'),
                  reasons=[], missing_evidence=[], evidence={},
                  limitations=['Kịch bản giả định, không phải lệnh đóng/mở.',
                               'EC tháng không xác định thời điểm vận hành.',
                               'Chưa kiểm tra cơ khí, triều tương lai và liên kết thủy lực.'])
    missing, invalid = result['missing_evidence'], []
    def number(container, key, label, nonnegative=False):
        value = container.get(key) if isinstance(container, dict) else None
        if value is None:
            missing.append(label)
            return None
        try:
            value = numeric(value, label)
            if nonnegative and value < 0:
                raise GateInputError(label)
            return value
        except GateInputError:
            invalid.append(label + ': cần số hữu hạn' + (' không âm' if nonnegative else ''))
            return None
    if data.get('schema_version') != 1 or policy.get('schema_version') != 1:
        invalid.append('Phiên bản hồ sơ phải là 1.')
    if not data.get('gate_code') or policy.get('gate_code') != data.get('gate_code'):
        invalid.append('Mã cống đầu vào và quy trình phải khớp.')
    mode = data.get('mode')
    if mode not in ('INTAKE', 'DRAIN'):
        invalid.append('Mục tiêu phải là INTAKE hoặc DRAIN.')
    observations = data.get('observations')
    observations = observations if isinstance(observations, dict) else {}
    values, times = {}, []
    parameter = policy.get('parameter') or {}
    if not isinstance(parameter, dict):
        parameter = {}
    basis = parameter.get('ec_basis')
    if parameter.get('name') != 'EC' or parameter.get('unit') != 'mS/m':
        invalid.append('Quy trình phải dùng EC, đơn vị mS/m.')
    if basis not in ('EC25', 'RAW'):
        missing.append('Cơ sở EC của quy trình (EC25 hoặc RAW)')
    datum = policy.get('vertical_datum')
    if not isinstance(datum, str) or not datum.strip():
        missing.append('Hệ cao độ chung')
    for key in ('outside_level', 'inside_level', 'outside_quality', 'inside_quality'):
        row = observations.get(key)
        row = row if isinstance(row, dict) else {}
        quality = key.endswith('quality')
        values[key] = number(row, 'value', key, quality)
        if row.get('gate_code') != data.get('gate_code'):
            invalid.append(key + ': mã cống không khớp')
        if row.get('unit') != ('mS/m' if quality else 'm'):
            invalid.append(key + ': đơn vị không tương thích')
        if quality and (row.get('parameter') != 'EC' or row.get('ec_basis') != basis):
            invalid.append(key + ': cơ sở EC không khớp quy trình')
        if not quality and row.get('vertical_datum') != datum:
            invalid.append(key + ': hệ cao độ không khớp')
        if not row.get('observed_at'):
            missing.append(key + ': thời điểm đo')
        else:
            try:
                times.append(stamp(row['observed_at']))
            except GateInputError:
                invalid.append(key + ': thời điểm đo không hợp lệ')
    if times and len(set(times)) > 1:
        invalid.append('Kịch bản yêu cầu số đo hai phía cùng thời điểm.')
    thresholds = policy.get('quality_thresholds')
    levels = policy.get('levels')
    opening = number(thresholds, 'open_below', 'Ngưỡng EC cho phép', True)
    closing = number(thresholds, 'close_at_or_above', 'Ngưỡng EC chặn', True)
    min_head = number(levels, 'min_head_m', 'Chênh mực nước tối thiểu', True)
    max_head = number(levels, 'max_abs_head_m', 'Chênh mực nước tối đa', True)
    low = number(levels, 'inside_min_m', 'Mực nước trong tối thiểu')
    high = number(levels, 'inside_max_m', 'Mực nước trong tối đa')
    for a, b, label in ((opening, closing, 'Ngưỡng EC'), (min_head, max_head, 'Chênh mực nước'), (low, high, 'Giới hạn mực nước')):
        if a is not None and b is not None and a >= b:
            invalid.append(label + ': cận dưới phải nhỏ hơn cận trên.')
    if invalid or missing:
        result.update(status='INVALID_INPUT' if invalid else 'INSUFFICIENT_DATA', reasons=invalid or ['Bổ sung các trường còn thiếu để mô phỏng.'])
        return result
    head = values['outside_level'] - values['inside_level']
    directional_head = head if mode == 'INTAKE' else -head
    result['evidence'] = dict(head_outside_minus_inside_m=head, directional_head_m=directional_head,
                              outside_ec_ms_m=values['outside_quality'], mode=mode)
    blocked, uncertain = [], []
    if directional_head <= 0 or directional_head < min_head:
        blocked.append('Chênh mực nước không đủ theo chiều ' + mode + '.')
    if abs(head) > max_head:
        blocked.append('Chênh mực nước vượt giới hạn kịch bản.')
    inside = values['inside_level']
    if mode == 'INTAKE' and inside >= high:
        blocked.append('Mực nước trong đã đạt giới hạn trên.')
    if mode == 'DRAIN' and inside <= low:
        blocked.append('Mực nước trong đã đạt giới hạn dưới.')
    saline_override = mode == 'DRAIN' and policy.get('allow_drainage_with_saline_outside') is True
    ec = values['outside_quality']
    if not saline_override:
        if ec >= closing:
            blocked.append('EC ngoài đạt hoặc vượt ngưỡng chặn.')
        elif ec >= opening:
            uncertain.append('EC nằm trong dải chuyển tiếp; không kết luận đủ điều kiện.')
    outcome = 'BLOCKED' if blocked else 'REVIEW_REQUIRED' if uncertain else 'CONDITIONS_MET'
    result.update(status='SIMULATED', simulation_outcome=outcome,
                  reasons=blocked + uncertain or ['Các điều kiện EC và thủy lực đã nhập phù hợp với mục tiêu ' + mode + ' trong kịch bản.'])
    if saline_override:
        result['reasons'].append('Kịch bản cho phép thoát nước khi EC ngoài cao; chỉ xét dòng chảy hướng ra ngoài.')
    return result
