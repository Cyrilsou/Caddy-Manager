from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    message: str
    expires_in: int


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None
    is_active: bool
    is_superadmin: bool
    role: str

    model_config = {"from_attributes": True}
