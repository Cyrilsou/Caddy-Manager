from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.backend import BackendCreate, BackendResponse, BackendUpdate
from app.services import backend_service

router = APIRouter(prefix="/backends", tags=["backends"])


@router.get("", response_model=list[BackendResponse])
async def list_backends(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    return await backend_service.list_backends(db)


@router.get("/{backend_id}", response_model=BackendResponse)
async def get_backend(backend_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    try:
        b = await backend_service.get_backend(db, backend_id)
        return BackendResponse.model_validate(b)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", response_model=BackendResponse, status_code=201)
async def create_backend(
    data: BackendCreate, request: Request,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    try:
        b = await backend_service.create_backend(db, data, user, request)
        return BackendResponse.model_validate(b)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{backend_id}", response_model=BackendResponse)
async def update_backend(
    backend_id: int, data: BackendUpdate, request: Request,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    try:
        b = await backend_service.update_backend(db, backend_id, data, user, request)
        return BackendResponse.model_validate(b)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{backend_id}", status_code=204)
async def delete_backend(
    backend_id: int, request: Request,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    try:
        await backend_service.delete_backend(db, backend_id, user, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{backend_id}/health-check")
async def health_check(
    backend_id: int,
    db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user),
):
    try:
        return await backend_service.check_backend_health(db, backend_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
