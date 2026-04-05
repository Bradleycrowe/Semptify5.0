from fastapi import APIRouter, HTTPException, Request

from app.core.user_id import get_role_from_user_id
from app.models.functionx_models import (
    FunctionXActionSetCreate,
    FunctionXActionSetDetail,
    FunctionXActionSetSummary,
    FunctionXExecuteRequest,
    FunctionXExecuteResponse,
)
from app.services.functionx_service import functionx_service

router = APIRouter(prefix="/api/functionx", tags=["FunctionX"])


def _get_user_role(request: Request) -> str:
    user_id = request.cookies.get("semptify_uid", "anonymous")
    role = get_role_from_user_id(user_id)
    if not role:
        role = "user"
    return role


def _require_roles(request: Request, allowed_roles: list[str]) -> str:
    role = _get_user_role(request)
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient role privileges")
    return role


@router.get("/health")
async def functionx_health() -> dict[str, str]:
    return {"status": "ok", "service": "functionx"}


@router.post("/sets", response_model=FunctionXActionSetDetail)
async def create_action_set(payload: FunctionXActionSetCreate, request: Request) -> FunctionXActionSetDetail:
    _require_roles(request, ["advocate", "manager", "legal", "admin"])
    try:
        return functionx_service.create_action_set(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/sets", response_model=list[FunctionXActionSetSummary])
async def list_action_sets(request: Request) -> list[FunctionXActionSetSummary]:
    _require_roles(request, ["user", "advocate", "manager", "legal", "admin"])
    return functionx_service.list_action_sets()


@router.get("/sets/{set_id}", response_model=FunctionXActionSetDetail)
async def get_action_set(set_id: str, request: Request) -> FunctionXActionSetDetail:
    _require_roles(request, ["user", "advocate", "manager", "legal", "admin"])
    item = functionx_service.get_action_set(set_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Action set not found")
    return item


@router.post("/sets/{set_id}/execute", response_model=FunctionXExecuteResponse)
async def execute_action_set(
    set_id: str,
    payload: FunctionXExecuteRequest,
    request: Request,
) -> FunctionXExecuteResponse:
    _require_roles(request, ["advocate", "manager", "legal", "admin"])
    result = functionx_service.execute_action_set(set_id=set_id, dry_run=payload.dry_run)
    if result is None:
        raise HTTPException(status_code=404, detail="Action set not found")
    return result
