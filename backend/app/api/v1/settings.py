from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.setting import Setting
from app.models.user import User
from app.schemas.setting import SettingResponse, SettingUpdate
from app.services.audit_service import log_audit

router = APIRouter(prefix="/settings", tags=["settings"])

MASKED_VALUE = "***"


@router.get("", response_model=list[SettingResponse])
async def list_settings(db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    result = await db.execute(select(Setting).order_by(Setting.key))
    settings_list = result.scalars().all()
    items = []
    for s in settings_list:
        items.append(SettingResponse(
            key=s.key,
            value=MASKED_VALUE if s.is_secret else s.value,
            is_secret=s.is_secret,
        ))
    return items


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str, data: SettingUpdate, request: Request,
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user),
):
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()

    if not setting:
        setting = Setting(key=key, value=data.value)
        db.add(setting)
    else:
        if setting.is_secret and data.value == MASKED_VALUE:
            return SettingResponse(key=setting.key, value=MASKED_VALUE, is_secret=setting.is_secret)
        setting.value = data.value

    await log_audit(db, user.id, "setting.update", "setting", None,
                    {"key": key, "is_secret": setting.is_secret}, request)
    await db.commit()
    await db.refresh(setting)

    return SettingResponse(
        key=setting.key,
        value=MASKED_VALUE if setting.is_secret else setting.value,
        is_secret=setting.is_secret,
    )
