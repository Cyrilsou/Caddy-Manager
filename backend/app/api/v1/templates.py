from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.domain_template import DomainTemplate
from app.models.user import User
from app.security.rbac import require_permission

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    force_https: bool = True
    enable_websocket: bool = False
    enable_cors: bool = False
    custom_headers: dict[str, str] | None = None
    strip_prefix: bool = False
    maintenance_mode: bool = False
    lb_policy: str = ""


class TemplateResponse(BaseModel):
    id: int
    name: str
    description: str | None
    force_https: bool
    enable_websocket: bool
    enable_cors: bool
    custom_headers: dict[str, str] | None
    strip_prefix: bool
    maintenance_mode: bool
    lb_policy: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[TemplateResponse])
async def list_templates(
    db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("domain.read")),
):
    result = await db.execute(select(DomainTemplate).order_by(DomainTemplate.name))
    return [TemplateResponse.model_validate(t) for t in result.scalars().all()]


@router.post("", response_model=TemplateResponse, status_code=201)
async def create_template(
    data: TemplateCreate,
    db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("domain.create")),
):
    existing = await db.execute(select(DomainTemplate).where(DomainTemplate.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Template '{data.name}' already exists")

    template = DomainTemplate(**data.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return TemplateResponse.model_validate(template)


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("domain.delete")),
):
    result = await db.execute(select(DomainTemplate).where(DomainTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.delete(template)
    await db.commit()
