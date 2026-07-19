from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from src.adapters.api.security import verify_admin_key

router = APIRouter(prefix="/v1/admin", tags=["Admin"])


class VerifyAdminKeyResponse(BaseModel):
    valid: bool


@router.get(
    "/verify-key",
    status_code=status.HTTP_200_OK,
    response_model=VerifyAdminKeyResponse,
    dependencies=[Depends(verify_admin_key)],
)
async def verify_admin_key_endpoint() -> VerifyAdminKeyResponse:
    return VerifyAdminKeyResponse(valid=True)
