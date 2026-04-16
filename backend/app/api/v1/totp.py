from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.security.totp import generate_totp_secret, get_totp_uri, generate_qr_base64, verify_totp

router = APIRouter(prefix="/auth/totp", tags=["2fa"])


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code: str
    uri: str


class TOTPVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class TOTPDisableRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


@router.post("/setup", response_model=TOTPSetupResponse)
async def setup_totp(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate TOTP secret and QR code. Must be confirmed with /confirm."""
    if user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")

    secret = generate_totp_secret()
    user.totp_secret = secret
    await db.commit()

    uri = get_totp_uri(secret, user.username)
    qr = generate_qr_base64(uri)

    return TOTPSetupResponse(secret=secret, qr_code=qr, uri=uri)


@router.post("/confirm")
async def confirm_totp(
    body: TOTPVerifyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify the first TOTP code to confirm setup."""
    if user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is already enabled")
    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="Run /setup first")

    if not verify_totp(user.totp_secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    user.totp_enabled = True
    await db.commit()

    return {"message": "2FA enabled successfully"}


@router.post("/disable")
async def disable_totp(
    body: TOTPDisableRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable 2FA. Requires a valid TOTP code."""
    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")

    if not verify_totp(user.totp_secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    user.totp_enabled = False
    user.totp_secret = None
    await db.commit()

    return {"message": "2FA disabled"}


@router.get("/status")
async def totp_status(user: User = Depends(get_current_user)):
    return {"enabled": user.totp_enabled}
