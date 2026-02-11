import csv
from io import StringIO
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from datetime import datetime
from io import BytesIO
from fastapi.responses import StreamingResponse
from app.core.deps import get_db
from app.routers.admin_access import ensure_admin_interface_aut, ensure_admin_interface_auth
from app.models.audit_log import AuditLog


router = APIRouter(
    prefix="/admin/audit-logs",
    tags=["Admin - Audit Logs"],
)

@router.get("/export/csv")
def export_audit_logs_csv(
    request: Request,
    db: Session = Depends(get_db),
    user_id: int | None = Query(None),
    action: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
):
    unauthorized = ensure_admin_interface_auth(request)
    if unauthorized:
        return unauthorized

    # فیلتر کردن لاگ‌ها بر اساس پارامترها
    query = db.query(AuditLog)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if date_from:
        query = query.filter(AuditLog.created_at >= date_from)
    if date_to:
        query = query.filter(AuditLog.created_at <= date_to)

    logs = query.order_by(AuditLog.created_at.desc()).all()

    # تولید فایل CSV
    output = StringIO()
    writer = csv.writer(output)

    # اضافه کردن سرآیندهای جدید به CSV
    writer.writerow([
        "ID", "User ID", "Action", "Entity", "Entity ID", "Description", "IP Address", "Created At",
    ])

    # نوشتن لاگ‌ها در CSV
    for log in logs:
        writer.writerow([
            log.id,
            log.user_id,
            log.action,
            log.entity,
            log.entity_id,
            log.description,
            log.ip_address,
            log.created_at,
        ])

    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"}
    )


@router.get("/export/excel")
def export_audit_logs_excel(
request: Request,
    db: Session = Depends(get_db),
    user_id: int | None = Query(None),
    action: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
):
    unauthorized = ensure_admin_interface_auth(request)
    if unauthorized:
        return unauthorized

    # فیلتر کردن لاگ‌ها
    query = db.query(AuditLog)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if date_from:
        query = query.filter(AuditLog.created_at >= date_from)
    if date_to:
        query = query.filter(AuditLog.created_at <= date_to)

    logs = query.order_by(AuditLog.created_at.desc()).all()

    # تولید فایل Excel
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Audit Logs"

    # اضافه کردن سرآیندها در Excel
    ws.append([
        "ID", "User ID", "Action", "Entity", "Entity ID", "Description", "IP Address", "Created At",
    ])

    # نوشتن لاگ‌ها در Excel
    for log in logs:
        ws.append([
            log.id,
            log.user_id,
            log.action,
            log.entity,
            log.entity_id,
            log.description,
            log.ip_address,
            log.created_at.strftime("%Y-%m-%d %H:%M"),
        ])

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=audit_logs.xlsx"}
    )

