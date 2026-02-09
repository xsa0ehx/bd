from typing import Optional

from pydantic import ValidationError
from fastapi import (
    APIRouter,
    Request,
    Form,
    HTTPException,
    status
)
from fastapi.responses import (
    RedirectResponse,
    HTMLResponse
)
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.deps import DBDep
from app.schemas.auth import RegisterRequest, GenderEnum
from app.services.auth_service import register_user, enforce_single_national_id_authentication
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.models.student_profile import StudentProfile
# ----------------------------
# Router & Templates
# ----------------------------
router = APIRouter(
    prefix="/ui-auth",
    tags=["UI Authentication"]
)

templates = Jinja2Templates(directory="app/templates")


# ----------------------------
# Home Page
# ----------------------------
@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "title": "سامانه مدیریت بسیج",
            "welcome_message": "به سامانه مدیریت بسیج دانشجویی خوش آمدید"
        }
    )


# ----------------------------
# Register (GET)
# ----------------------------
@router.get("/register", response_class=HTMLResponse)
async def show_register_page(
    request: Request,
    success_message: Optional[str] = None,
    error_message: Optional[str] = None
):
    return templates.TemplateResponse(
        "auth/register.html",
        {
            "request": request,
            "title": "ثبت‌نام در سامانه",
            "success_message": success_message,
            "error_message": error_message,
            "genders": [
                {"value": "brother", "label": "برادر"},
                {"value": "sister", "label": "خواهر"}
            ]
        }
    )


# ----------------------------
# Register (POST)
# ----------------------------
@router.post("/register", response_class=HTMLResponse)
async def submit_register(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    student_number: str = Form(...),
    national_code: str = Form(...),
    phone_number: str = Form(...),
    gender: str = Form(...),
    address: Optional[str] = Form(""),
    db: Session = DBDep()
):
    try:
        # تبدیل gender به Enum
        gender_enum = GenderEnum(gender)

        register_data = RegisterRequest(
            first_name=first_name,
            last_name=last_name,
            student_number=student_number,
            national_code=national_code,
            phone_number=phone_number,
            gender=gender_enum,
            address=address or None
        )

        register_user(db, register_data)

        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "title": "ورود به سامانه",
                "success_message": "ثبت‌نام با موفقیت انجام شد. لطفاً وارد شوید.",
                "student_number": student_number
            },
            status_code=status.HTTP_201_CREATED
        )

    except ValidationError:
        error_message = "اطلاعات ثبت‌نام نامعتبر است."
    except ValueError:
        # خطای enum جنسیت
        error_message = "جنسیت انتخاب‌شده معتبر نیست."

    except HTTPException as e:
        error_message = e.detail

    return templates.TemplateResponse(
        "auth/register.html",
        {
            "request": request,
            "title": "ثبت‌نام در سامانه",
            "error_message": error_message,
            "form_data": {
                "first_name": first_name,
                "last_name": last_name,
                "student_number": student_number,
                "national_code": national_code,
                "phone_number": phone_number,
                "gender": gender,
                "address": address
            },
            "genders": [
                {"value": "brother", "label": "برادر"},
                {"value": "sister", "label": "خواهر"}
            ]
        },
        status_code=400
    )


# ----------------------------
# Login (GET)
# ----------------------------
@router.get("/login", response_class=HTMLResponse)
async def show_login_page(
    request: Request,
    success_message: Optional[str] = None,
    error_message: Optional[str] = None
):
    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "title": "ورود به سامانه",
            "success_message": success_message,
            "error_message": error_message,
            "redirect_url": request.query_params.get(
                "redirect", "/ui-auth/dashboard"
            )
        }
    )


# ----------------------------
# Login (POST)
# ----------------------------
@router.post("/login", response_class=HTMLResponse)
async def submit_login(
    request: Request,
    national_code: str = Form(...),  # کد ملی
    password: str = Form(...),  # شماره دانشجویی
    remember_me: Optional[str] = Form(None),
    redirect_url: Optional[str] = Form("/ui-auth/dashboard"),
    db: Session = DBDep()
):
    if not national_code.isdigit() or len(national_code) != 10:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "title": "ورود به سامانه",
                "error_message": "کد ملی باید شامل ۱۰ رقم باشد.",
                "national_code": national_code
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )
    if not password.isdigit():
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "title": "ورود به سامانه",
                "error_message": "شماره دانشجویی باید فقط شامل رقم باشد.",
                "national_code": national_code
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    user = (
        db.query(User)
        .join(StudentProfile, StudentProfile.user_id == User.id)
        .filter(StudentProfile.national_code == national_code)
        .first()
    )

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "title": "ورود به سامانه",
                "error_message": "کد ملی یا شماره دانشجویی نادرست است.",
                "national_code": national_code
            },
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "title": "ورود به سامانه",
                "error_message": "حساب کاربری شما غیرفعال شده است.",
                "national_code": national_code
            },
            status_code=status.HTTP_403_FORBIDDEN
        )

    try:
        enforce_single_national_id_authentication(db, user)
    except HTTPException as e:
        return templates.TemplateResponse(
            "auth/login.html",
            {
                "request": request,
                "title": "ورود به سامانه",
                "error_message": e.detail,
                "national_code": national_code
            },
            status_code=status.HTTP_403_FORBIDDEN
        )

    access_token = create_access_token(
        data={
            "sub": user.student_number,
            "user_id": user.id,
            "national_code": user.profile.national_code if user.profile else None
        }
    )

    max_age = 30 * 24 * 60 * 60 if remember_me else 24 * 60 * 60

    response = RedirectResponse(
        url=redirect_url,
        status_code=status.HTTP_303_SEE_OTHER
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=max_age,
        httponly=True,
        secure=False,  # در production → True
        samesite="lax"
    )

    return response


# ----------------------------
# Logout
# ----------------------------
@router.get("/logout")
async def logout_user():
    response = RedirectResponse(
        url="/ui-auth/login",
        status_code=status.HTTP_303_SEE_OTHER
    )
    response.delete_cookie("access_token")
    return response


# ----------------------------
# Dashboard
# ----------------------------
@router.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard(
    request: Request,
    db: Session = DBDep()
):
    token = request.cookies.get("access_token")

    if not token:
        return RedirectResponse(
            url="/ui-auth/login?redirect=/ui-auth/dashboard",
            status_code=status.HTTP_303_SEE_OTHER
        )

    return templates.TemplateResponse(
        "dashboard/main.html",
        {
            "request": request,
            "title": "داشبورد کاربری",
            "message": "به داشبورد خوش آمدید"
        }
    )
