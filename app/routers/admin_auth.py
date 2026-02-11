from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from app.core.deps import DBDep
from app.schemas.auth import AdminLoginRequest, Token
from app.services.auth_service import authenticate_admin_password, create_token_for_user

router = APIRouter(prefix="/admin", tags=["Admin Authentication"])


@router.post("/login", response_model=Token, summary="ورود مدیر با رمز عبور")
async def admin_login(
    data: AdminLoginRequest,
    db=DBDep(),
):
    """ورود مدیر با رمز عبور اختصاصی ادمین."""
    try:
        admin_user = authenticate_admin_password(db, data.password)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در بررسی اطلاعات ورود مدیر. لطفاً دوباره تلاش کنید.",
        ) from exc

    if not admin_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="رمز عبور مدیر نادرست است",
        )

    if not admin_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="حساب کاربری مدیر غیرفعال شده است",
        )

    return create_token_for_user(admin_user)