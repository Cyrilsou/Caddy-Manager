from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.certificate import Certificate
from app.models.user import User
from app.schemas.certificate import CertificateResponse
from app.security.rbac import require_permission

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.get("", response_model=list[CertificateResponse])
async def list_certificates(db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("cert.read"))):
    result = await db.execute(select(Certificate).order_by(Certificate.hostname))
    return [CertificateResponse.model_validate(c) for c in result.scalars().all()]


@router.get("/{cert_id}", response_model=CertificateResponse)
async def get_certificate(cert_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("cert.read"))):
    result = await db.execute(select(Certificate).where(Certificate.id == cert_id))
    cert = result.scalar_one_or_none()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return CertificateResponse.model_validate(cert)


@router.post("/refresh")
async def refresh_certificates(_: User = Depends(require_permission("cert.refresh"))):
    from app.tasks.cert_checker import run_cert_checks
    await run_cert_checks()
    return {"message": "Certificate check triggered"}
