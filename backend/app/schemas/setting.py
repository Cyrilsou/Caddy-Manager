from pydantic import BaseModel


class SettingResponse(BaseModel):
    key: str
    value: str
    is_secret: bool

    model_config = {"from_attributes": True}


class SettingUpdate(BaseModel):
    value: str
