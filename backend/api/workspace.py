"""HTTP adapters for workspace browsing, archived estimates and dossier review."""
import csv
import io
import json
from typing import Annotated
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response
from backend.services import workspace, forecasts, gates, spatial_simulation
from backend.api.multivariate import router as multivariate_router
from backend.api.dss_storage import router as dss_storage_router

router = APIRouter()
router.include_router(multivariate_router)
router.include_router(dss_storage_router)

router.add_api_route('/summary', workspace.summary, methods=['GET'])
router.add_api_route('/stations', workspace.stations, methods=['GET'])
router.add_api_route(
    '/stations/{site_code}/observations', workspace.observations, methods=['GET']
)
router.add_api_route('/experiments/{experiment_id}', workspace.experiment, methods=['GET'])
router.add_api_route('/experiments/{experiment_id}/next-forecast', forecasts.next_forecast, methods=['GET'])
router.add_api_route('/boundaries', workspace.boundaries, methods=['GET'])
router.add_api_route('/gates', workspace.gates, methods=['GET'])
router.add_api_route('/database-gates', workspace.database_gates, methods=['GET'])
router.add_api_route('/future-forecast', forecasts.monthly_estimates, methods=['GET'])
router.add_api_route('/monthly-estimates', forecasts.monthly_estimates, methods=['GET'])


@router.get('/simulation/corridor')
def simulation_corridor():
    return spatial_simulation.simulation_corridor()


@router.get('/simulation/timeline')
def simulation_timeline():
    return spatial_simulation.simulation_timeline()


@router.get('/simulation/frame')
def simulation_frame(
    year_month: Annotated[str, Query(pattern=r'^\d{4}-(0[1-9]|1[0-2])$')],
    open_below_ec: Annotated[float, Query(ge=0, allow_inf_nan=False)] = 120.0,
    close_above_ec: Annotated[float, Query(gt=0, allow_inf_nan=False)] = 150.0,
):
    return spatial_simulation.simulation_frame(year_month, open_below_ec, close_above_ec)


@router.get('/database-gates/{gate_code}/candidate-stations')
def candidate_stations(
    gate_code: str,
    radius_km: Annotated[float, Query(gt=0, le=200)] = 50,
):
    return workspace.candidate_stations(gate_code, radius_km)


@router.get('/gate-template/{kind}')
def gate_template(
    kind: str,
    gate_code: Annotated[str | None, Query(max_length=64)] = None,
):
    return workspace.gate_template(kind, gate_code)


@router.post('/gate-evaluation')
async def gate_evaluation(request: Request):
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > 262144:
            raise HTTPException(413, detail='Gate dossier exceeds 256 KiB.')
        chunks.append(chunk)
    try:
        def invalid_constant(value):
            raise ValueError('Non-finite JSON number.')
        payload = json.loads(b''.join(chunks), parse_constant=invalid_constant)
        policy, data = payload['policy'], payload['input']
        if not isinstance(policy, dict) or not isinstance(data, dict):
            raise ValueError('Object required.')
        return gates.review_dossier(policy, data)
    except (
        ValueError, KeyError, TypeError, AttributeError, OverflowError, RecursionError
    ) as exc:
        raise HTTPException(
            422, detail='Expected a JSON object with policy and input objects.'
        ) from exc


@router.get('/monthly-estimates/export')
def export_estimates(station: str | None = None):
    result = forecasts.monthly_estimates(station)
    stream = io.StringIO(newline='')
    fields = list(result['items'][0]) + [
        'data_kind', 'unit', 'live_forecast_available', 'gate_decision_eligible'
    ]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in result['items']:
        writer.writerow(
            dict(row, **{field: result[field] for field in fields if field not in row})
        )
    return Response(
        stream.getvalue(),
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': 'attachment; filename="monthly-ec-estimates.csv"'},
    )


@router.get('/artifacts/{experiment_id}/{filename}')
def artifact(experiment_id: str, filename: str):
    return FileResponse(
        workspace.artifact_path(experiment_id, filename),
        filename=experiment_id + '_' + filename,
    )


@router.get('/gate-source')
def gate_source():
    return FileResponse(
        workspace.ROOT / 'data/raw/gates/dongthap_gate_catalog_2025.pdf',
        media_type='application/pdf',
    )
