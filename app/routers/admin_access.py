from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from hmac import compare_digest

from fastapi import APIRouter, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.confing import settings

router = APIRouter(prefix="/admin", tags=["Admin Interface"])

ADMIN_AUTH_COOKIE = "admin_interface_token"

_failed_attempts: dict[str, datetime] = {}
_csrf_tokens: dict[str, str] = {}
_active_sessions: dict[str, datetime] = {}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _request_identity(request: Request) -> str:
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    return f"{client_ip}:{user_agent}"


def _cleanup_expired_sessions() -> None:
    now = _now_utc()
    expired_tokens = [token for token, exp in _active_sessions.items() if exp <= now]
    for token in expired_tokens:
        _active_sessions.pop(token, None)


def _read_lock_until(identity: str) -> datetime | None:
    lock_until = _failed_attempts.get(identity)
    if lock_until and lock_until > _now_utc():
        return lock_until

    _failed_attempts.pop(identity, None)
    return None


def _remaining_seconds(lock_until: datetime) -> int:
    delta = lock_until - _now_utc()
    return max(0, int(delta.total_seconds()))


def ensure_admin_interface_auth(request: Request) -> RedirectResponse | None:
    _cleanup_expired_sessions()

    token = request.cookies.get(ADMIN_AUTH_COOKIE)
    if token and token in _active_sessions:
        return None

    return RedirectResponse(
        url="/admin/login",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/login", response_class=HTMLResponse)
def show_admin_login(request: Request):
    identity = _request_identity(request)
    csrf_token = _csrf_tokens.get(identity)
    if not csrf_token:
        csrf_token = secrets.token_urlsafe(32)
        _csrf_tokens[identity] = csrf_token

    lock_until = _read_lock_until(identity)
    remaining_seconds = _remaining_seconds(lock_until) if lock_until else 0

    return request.app.state.templates.TemplateResponse(
        "admin/login.html",
        {
            "request": request,
            "title": "ورود مدیریت",
            "csrf_token": csrf_token,
            "remaining_seconds": remaining_seconds,
            "lockout_minutes": settings.admin_lockout_minutes,
            "error_message": None,
        },
    )


@router.post("/login", response_class=HTMLResponse)
def submit_admin_login(
    request: Request,
    password: str = Form(...),
    csrf_token: str = Form(...),
):
    identity = _request_identity(request)
    session_csrf_token = _csrf_tokens.get(identity)

    if not session_csrf_token or not compare_digest(csrf_token, session_csrf_token):
        return request.app.state.templates.TemplateResponse(
            "admin/login.html",
            {
                "request": request,
                "title": "ورود مدیریت",
                "csrf_token": session_csrf_token or "",
                "remaining_seconds": 0,
                "lockout_minutes": settings.admin_lockout_minutes,
                "error_message": "درخواست نامعتبر است. لطفاً صفحه را بازخوانی کنید.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    lock_until = _read_lock_until(identity)
    if lock_until:
        remaining_seconds = _remaining_seconds(lock_until)
        return request.app.state.templates.TemplateResponse(
            "admin/login.html",
            {
                "request": request,
                "title": "ورود مدیریت",
                "csrf_token": session_csrf_token,
                "remaining_seconds": remaining_seconds,
                "lockout_minutes": settings.admin_lockout_minutes,
                "error_message": "Incorrect password. Please wait for 15 minutes before trying again.",
            },
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    if compare_digest(password, settings.admin_interface_password):
        session_token = secrets.token_urlsafe(32)
        _active_sessions[session_token] = _now_utc() + timedelta(hours=8)
        _failed_attempts.pop(identity, None)

        response = RedirectResponse(
            url="/admin/dashboard",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        response.set_cookie(
            key=ADMIN_AUTH_COOKIE,
            value=session_token,
            max_age=8 * 60 * 60,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
        )
        return response

    lock_until = _now_utc() + timedelta(minutes=settings.admin_lockout_minutes)
    _failed_attempts[identity] = lock_until

    return request.app.state.templates.TemplateResponse(
        "admin/login.html",
        {
            "request": request,
            "title": "ورود مدیریت",
            "csrf_token": session_csrf_token,
            "remaining_seconds": _remaining_seconds(lock_until),
            "lockout_minutes": settings.admin_lockout_minutes,
            "error_message": "Incorrect password. Please wait for 15 minutes before trying again.",
        },
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


@router.get("/logout")
def admin_logout(request: Request):
    token = request.cookies.get(ADMIN_AUTH_COOKIE)
    if token:
        _active_sessions.pop(token, None)

    response = RedirectResponse(
        url="/admin/login",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.delete_cookie(ADMIN_AUTH_COOKIE)
    return response