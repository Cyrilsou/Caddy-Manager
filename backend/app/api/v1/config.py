from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.config import (
    CaddyStatusResponse,
    ConfigApplyResponse,
    ConfigDiffResponse,
    ConfigPreviewResponse,
    ConfigVersionDetailResponse,
    ConfigVersionResponse,
)
from app.services import config_service
from app.services.caddy_service import caddy_service

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/current")
async def get_current_config(_: User = Depends(get_current_user)):
    config = await caddy_service.get_current_config()
    if config is None:
        raise HTTPException(status_code=503, detail="Cannot reach Caddy admin API")
    return config


@router.get("/preview", response_model=ConfigPreviewResponse)
async def preview_config(
    db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user),
):
    return await config_service.preview_config(db)


@router.post("/apply", response_model=ConfigApplyResponse)
async def apply_config(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return await config_service.apply_config(db, user, request)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/versions", response_model=list[ConfigVersionResponse])
async def list_versions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    versions = await config_service.list_versions(db, page, per_page)
    return [ConfigVersionResponse.model_validate(v) for v in versions]


@router.get("/versions/{version_id}", response_model=ConfigVersionDetailResponse)
async def get_version(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        v = await config_service.get_version(db, version_id)
        return ConfigVersionDetailResponse.model_validate(v)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/versions/{version_id}/rollback", response_model=ConfigApplyResponse)
async def rollback_version(
    version_id: int, request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        return await config_service.rollback_config(db, version_id, user, request)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/versions/{version_id}/diff", response_model=ConfigDiffResponse)
async def get_diff(
    version_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        return await config_service.get_diff(db, version_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/caddy-status", response_model=CaddyStatusResponse)
async def caddy_status(_: User = Depends(get_current_user)):
    reachable = await caddy_service.is_reachable()
    config = await caddy_service.get_current_config() if reachable else None
    return CaddyStatusResponse(
        reachable=reachable,
        config_loaded=config is not None,
        message="Caddy is running" if reachable else "Cannot reach Caddy admin API",
    )
