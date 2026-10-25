"""Compatibility imports for existing scripts and legacy API consumers."""
from fastapi import APIRouter
from backend.api.workspace import router as workspace_router
from backend.domain.workspace import validate_bundle
from backend.services.workspace import load_bundle

router = APIRouter(prefix='/api/v1/research', tags=['Legacy workspace'])
router.include_router(workspace_router)
