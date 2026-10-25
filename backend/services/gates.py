"""Review declared gate dossiers without verifying or authorizing operations."""
from datetime import datetime, timezone
from backend.domain.gates import evaluate
from backend.domain.gate_simulation import simulate

OBSERVATION_LABELS = {
    'outside_level': 'Mực nước phía ngoài cống',
    'inside_level': 'Mực nước phía trong cống',
    'outside_quality': 'Chỉ số EC phía ngoài cống',
    'inside_quality': 'Chỉ số EC phía trong cống',
}


def review_dossier(policy, data):
    result = simulate(policy, data) if data.get('evaluation_mode') == 'SIMULATION' else evaluate(policy, data)
    observations = data.get('observations')
    observations = observations if isinstance(observations, dict) else {}
    checklist = []
    for key, label in OBSERVATION_LABELS.items():
        record = observations.get(key)
        present = isinstance(record, dict) and record.get('value') is not None
        checklist.append(dict(code=key, label=label, declared_present=present))
    result.update(
        checklist=checklist,
        missing_evidence=list(dict.fromkeys(
            [entry['code'] for entry in checklist if not entry['declared_present']]
            + result.get('missing_evidence', [])
            + ([] if result.get('evaluation_mode') == 'SIMULATION' else ['SERVER_VERIFIED_GATE_EVIDENCE'])
        )),
        declarations_verified_by_server=False,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        note=(
            ('Hypothetical scenario only. ' if result.get('evaluation_mode') == 'SIMULATION' else 'Dossier review only. ')
            + 'Submitted declarations are not server-verified '
            'evidence; monthly EC cannot determine gate switching times.'
        ),
    )
    return result
