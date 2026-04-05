from fastapi import APIRouter, HTTPException

from app.models.functionx_models import (
    FunctionXActionSetCreate,
    FunctionXActionSetDetail,
    FunctionXActionSetSummary,
    FunctionXExecuteRequest,
    FunctionXExecuteResponse,
)
from app.services.functionx_service import functionx_service

router = APIRouter(prefix="/api/functionx", tags=["FunctionX"])


@router.get("/health")
async def functionx_health() -> dict[str, str]:
    return {"status": "ok", "service": "functionx"}


@router.post("/sets", response_model=FunctionXActionSetDetail)
async def create_action_set(payload: FunctionXActionSetCreate) -> FunctionXActionSetDetail:
    try:
        return functionx_service.create_action_set(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/sets", response_model=list[FunctionXActionSetSummary])
async def list_action_sets() -> list[FunctionXActionSetSummary]:
    return functionx_service.list_action_sets()


@router.get("/sets/{set_id}", response_model=FunctionXActionSetDetail)
async def get_action_set(set_id: str) -> FunctionXActionSetDetail:
    item = functionx_service.get_action_set(set_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Action set not found")
    return item


@router.post("/sets/{set_id}/execute", response_model=FunctionXExecuteResponse)
async def execute_action_set(set_id: str, payload: FunctionXExecuteRequest) -> FunctionXExecuteResponse:
    result = functionx_service.execute_action_set(set_id=set_id, dry_run=payload.dry_run)
    if result is None:
        raise HTTPException(status_code=404, detail="Action set not found")
    return result
