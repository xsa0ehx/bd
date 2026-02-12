from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload

from app.core.confing import settings

from app.core.deps import get_db
from app.core.security import verify_password
from app.models.user import User
from app.routers.admin_access import ensure_admin_interface_auth
from app.services.audit_service import get_audit_logs, get_simple_audit_stats
from app.services.admin_auth_service import is_admin_authenticated

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])
templates = Jinja2Templates(directory="app/templates")

ADMIN_COOKIE_NAME = "admin_access_token"
ADMIN_LOGIN_ATTEMPT_LIMIT = 5
ADMIN_LOGIN_BLOCK_MINUTES = 15
ADMIN_AUTH_ALGORITHM = "HS256"
ADMIN_DEFAULT_PASSWORD_HASH = "$2b$12$X1QCO5L9pRVF/iaqvWnToOX.2tjb2BY12OZ5dpun4.DjtTmpJgzd."
ADMIN_PASSWORD_HASH = settings.admin_password_hash or ADMIN_DEFAULT_PASSWORD_HASH

failed_login_attempts: dict[str, dict[str, object]] = {}


def _client_identifier(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _is_blocked(client_id: str) -> tuple[bool, Optional[datetime]]:
    attempt_data = failed_login_attempts.get(client_id)
    if not attempt_data:
        return False, None

    blocked_until = attempt_data.get("blocked_until")
    if isinstance(blocked_until, datetime):
        now = datetime.now(timezone.utc)
        if blocked_until > now:
            return True, blocked_until

    # block expired
    failed_login_attempts.pop(client_id, None)
    return False, None


def _register_failed_attempt(client_id: str) -> None:
    now = datetime.now(timezone.utc)
    attempt_data = failed_login_attempts.setdefault(client_id, {"count": 0, "blocked_until": None})
    attempt_data["count"] = int(attempt_data.get("count", 0)) + 1

    if attempt_data["count"] >= ADMIN_LOGIN_ATTEMPT_LIMIT:
        attempt_data["blocked_until"] = now + timedelta(minutes=ADMIN_LOGIN_BLOCK_MINUTES)
        attempt_data["count"] = 0


def _reset_attempts(client_id: str) -> None:
    failed_login_attempts.pop(client_id, None)


def _build_admin_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": "admin-portal",
        "role": "admin_portal",
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ADMIN_AUTH_ALGORITHM)


def _is_authenticated_admin(request: Request) -> bool:
    token = request.cookies.get(ADMIN_COOKIE_NAME)
    if not token:
        return False

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ADMIN_AUTH_ALGORITHM])
    except JWTError:
        return False

    return payload.get("role") == "admin_portal"


@router.get("/login", response_class=HTMLResponse)
def admin_login_page(request: Request, error_message: Optional[str] = None):
    client_id = _client_identifier(request)
    blocked, blocked_until = _is_blocked(client_id)
    return templates.TemplateResponse(
        "admin/login.html",
        {
            "request": request,
            "error_message": error_message,
            "is_blocked": blocked,
            "blocked_until": blocked_until,
        },
    )


@router.post("/login", response_class=HTMLResponse)
def admin_login_submit(
    request: Request,
    password: str = Form(...),
):
    client_id = _client_identifier(request)
    blocked, blocked_until = _is_blocked(client_id)
    if blocked:
        return templates.TemplateResponse(
            "admin/login.html",
            {
                "request": request,
                "error_message": "به دلیل تلاش‌های ناموفق متعدد، ورود موقتاً مسدود شده است.",
                "is_blocked": True,
                "blocked_until": blocked_until,
            },
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if not verify_password(password, ADMIN_PASSWORD_HASH):
        _register_failed_attempt(client_id)
        blocked_after_failure, blocked_until = _is_blocked(client_id)
        error_message = "رمز عبور مدیر نادرست است."
        if blocked_after_failure:
            error_message += " ورود شما برای ۱۵ دقیقه مسدود شد."

        return templates.TemplateResponse(
            "admin/login.html",
            {
                "request": request,
                "error_message": error_message,
                "is_blocked": blocked_after_failure,
                "blocked_until": blocked_until,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    _reset_attempts(client_id)
    token = _build_admin_token()

    response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    return response


@router.get("/logout")
def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(ADMIN_COOKIE_NAME)
    return response
templates = Jinja2Templates(directory="app/templates")

@router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard(
        request: Request,
        db: Session = Depends(get_db),
):
    """داشبورد ادمین با نمایش لاگ‌ها و کاربران ثبت‌شده."""
    if not is_admin_authenticated(request):
        return RedirectResponse(
            url="/ui-auth/admin/login?redirect=/admin/dashboard",
            status_code=303,
        )

    """داشبورد ادمین - فقط آخرین لاگ‌ها"""

    users = (
        db.query(User)
        .options(joinedload(User.profile), joinedload(User.role))
        .order_by(User.created_at.desc())
        .all()
    )

    recent_logs = get_audit_logs(db, limit=10)
    stats = get_simple_audit_stats(db)

    # اضافه کردن شماره دانشجویی و کد ملی به لاگ‌ها
    users = (
        db.query(User)
        .options(joinedload(User.profile), joinedload(User.role))
        .order_by(User.created_at.desc())
        .limit(50)
        .all()
    )
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "users": users,
            "recent_logs": recent_logs.get("logs", []),
            "stats": stats,
        },
    )

@router.get("/users/{user_id}", response_class=HTMLResponse)
def admin_user_details(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    if not _is_authenticated_admin(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    user = (
        db.query(User)
        .options(joinedload(User.profile), joinedload(User.role))
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد")

    return templates.TemplateResponse(
        "admin/user_details.html",
        {
            "request": request,
            "user": user,
        },
    )



@router.get("/audit-logs", response_class=HTMLResponse)
def audit_logs_page(
        request: Request,
        db: Session = Depends(get_db),
        skip: int = Query(0, ge=0, description="تعداد رکوردهای رد شده"),
        limit: int = Query(50, ge=1, le=200, description="تعداد رکوردهای قابل نمایش"),
        date_from: Optional[datetime] = Query(None, description="تاریخ شروع"),
        date_to: Optional[datetime] = Query(None, description="تاریخ پایان"),
        action: Optional[str] = Query(None, description="فیلتر بر اساس عمل"),
        user_id: Optional[int] = Query(None, description="فیلتر بر اساس کاربر"),

):

    if not is_admin_authenticated(request):
        return RedirectResponse(
            url="/ui-auth/admin/login?redirect=/admin/audit-logs",
            status_code=303,
        )

    result = get_audit_logs(
        db=db,
        skip=skip,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
        action=action,
        user_id=user_id
    )

    return templates.TemplateResponse(
        "admin/audit_logs.html",
        {
            "request": request,
            "logs": result.get("logs", []),
            "total": result.get("total", 0),
            "skip": skip,
            "limit": limit,
            "has_more": result.get("has_more", False),
            "filters": {
                "user_id": user_id or "",
                "action": action or "",
                "date_from": date_from.isoformat() if date_from else "",
                "date_to": date_to.isoformat() if date_to else "",
            },
        },
    )


