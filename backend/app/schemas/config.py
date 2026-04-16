from datetime import datetime
from pydantic import BaseModel


class ConfigPreviewResponse(BaseModel):
    config_json: dict
    has_changes: bool
    change_summary: str | None = None


class ConfigApplyResponse(BaseModel):
    success: bool
    version_number: int
    message: str


class ConfigVersionResponse(BaseModel):
    id: int
    version_number: int
    config_hash: str
    is_active: bool
    applied_at: datetime | None
    applied_by_id: int | None
    rollback_of_id: int | None
    change_summary: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConfigVersionDetailResponse(ConfigVersionResponse):
    config_json: str


class ConfigDiffResponse(BaseModel):
    old_version: int
    new_version: int
    diff: str


class CaddyStatusResponse(BaseModel):
    reachable: bool
    config_loaded: bool
    message: str
