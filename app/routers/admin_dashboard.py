from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.security import get_current_admin
from app.models.user import User
from app.routers.admin_access import ensure_admin_interface_auth
from app.services.audit_service import (
    get_audit_logs,
    get_simple_audit_stats
)

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
def admin_dashboard(
        request: Request,
        db: Session = Depends(get_db),
):

    unauthorized=ensure_admin_interface_auth(request)
    if unauthorized:
        return unauthorized

    """داشبورد ادمین - فقط آخرین لاگ‌ها"""

    # دریافت آخرین لاگ‌ها (۱۰ مورد)
    recent_logs = get_audit_logs(db, limit=10)

    # دریافت آمار ساده
    stats = get_simple_audit_stats(db)

    # اضافه کردن شماره دانشجویی و کد ملی به لاگ‌ها
    for log in recent_logs.get("logs", []):
        if log.user:
            log.student_number = log.user.student_number  # شماره دانشجویی
            log.national_code = log.user.profile.national_code if log.user.profile else None  # کد ملی

    return request.app.state.templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "recent_logs": recent_logs.get("logs", []),
            "stats": stats,
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
    """صفحه نمایش لاگ‌های سیستم"""
    unauthorized = ensure_admin_interface_auth(request)
    if unauthorized:
        return unauthorized

    # دریافت لاگ‌ها
    result = get_audit_logs(
        db=db,
        skip=skip,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
        action=action,
        user_id=user_id
    )

    # اضافه کردن اطلاعات بیشتر به لاگ‌ها
    for log in result.get("logs", []):
        if log.user:
            log.student_number = log.user.student_number
            log.national_code = log.user.profile.national_code if log.user.profile else None

    return request.app.state.templates.TemplateResponse(
        "admin/audit_logs.html",
        {
            "request": request,
            "logs": result.get("logs", []),
            "total": result.get("total", 0),
            "skip": skip,
            "limit": limit,
            "has_more": result.get("has_more", False),
            "date_from": date_from,
            "date_to": date_to,
            "action": action,
            "user_id": user_id,
        },
    )


@router.get("/api/audit-logs")
def list_audit_logs_api(
        request: Request,
        db: Session = Depends(get_db),
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=200),
        date_from: Optional[datetime] = Query(None),
        date_to: Optional[datetime] = Query(None),
        action: Optional[str] = Query(None),
        user_id: Optional[int] = Query(None),
):
    """API دریافت لیست لاگ‌ها (برای AJAX/API calls)"""
    unauthorized = ensure_admin_interface_auth(request)
    if unauthorized:
        return unauthorized

    result = get_audit_logs(
        db=db,
        skip=skip,
        limit=limit,
        date_from=date_from,
        date_to=date_to,
        action=action,
        user_id=user_id
    )

    # اضافه کردن اطلاعات بیشتر به لاگ‌ها
    for log in result.get("logs", []):
        if log.user:
            log.student_number = log.user.student_number
            log.national_code = log.user.profile.national_code if log.user.profile else None

    return result
