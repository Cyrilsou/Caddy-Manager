from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.backend import BackendCreate, BackendResponse, BackendUpdate
from app.security.rbac import require_permission
from app.services import backend_service

router = APIRouter(prefix="/backends", tags=["backends"])
limiter = Limiter(key_func=get_remote_address)


@router.get("", response_model=list[BackendResponse])
async def list_backends(db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("backend.read"))):
    return await backend_service.list_backends(db)


@router.get("/{backend_id}", response_model=BackendResponse)
async def get_backend(backend_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("backend.read"))):
    try:
        b = await backend_service.get_backend(db, backend_id)
        return BackendResponse.model_validate(b)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", response_model=BackendResponse, status_code=201)
async def create_backend(
    data: BackendCreate, request: Request,
    db: AsyncSession = Depends(get_db), user: User = Depends(require_permission("backend.create")),
):
    try:
        b = await backend_service.create_backend(db, data, user, request)
        return BackendResponse.model_validate(b)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{backend_id}", response_model=BackendResponse)
async def update_backend(
    backend_id: int, data: BackendUpdate, request: Request,
    db: AsyncSession = Depends(get_db), user: User = Depends(require_permission("backend.update")),
):
    try:
        b = await backend_service.update_backend(db, backend_id, data, user, request)
        return BackendResponse.model_validate(b)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{backend_id}", status_code=204)
async def delete_backend(
    backend_id: int, request: Request,
    db: AsyncSession = Depends(get_db), user: User = Depends(require_permission("backend.delete")),
):
    try:
        await backend_service.delete_backend(db, backend_id, user, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{backend_id}/health-check")
@limiter.limit("10/minute")
async def health_check(
    request: Request,
    backend_id: int,
    db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("backend.read")),
):
    try:
        return await backend_service.check_backend_health(db, backend_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
