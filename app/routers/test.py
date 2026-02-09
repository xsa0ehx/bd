# app/routers/test.py - اصلاح شده
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.deps import DBDep, CurrentUser, AdminDep
from app.models.user import User
from app.models.role import Role
from app.models.student_profile import StudentProfile
from app.schemas.user import UserOut
from app.schemas.auth import Token

router = APIRouter(
    prefix="/test",
    tags=["Test & Debug"]
)


@router.get(
    "/",
    summary="صفحه اصلی تست",
    description="صفحه اصلی برای تست API"
)
async def test_root():
    """
    صفحه اصلی تست - سلامت سیستم را چک می‌کند.
    """
    return {
        "message": "API تست بسیج فعال است! 🚀",
        "status": "active",
        "endpoints": {
            "auth_test": "/test/auth",
            "db_test": "/test/db",
            "me": "/test/me",
            "admin_only": "/test/admin",
            "users": "/test/users",
            "roles": "/test/roles"
        },
        "version": "1.0.0"
    }


@router.get(
    "/auth",
    summary="تست احراز هویت",
    description="تست سلامت سیستم احراز هویت"
)
async def test_auth():
    """
    تست سلامت سیستم احراز هویت.
    """
    return {
        "auth_system": "JWT Token Based",
        "status": "active",
        "token_url": "/auth/login",
        "register_url": "/auth/register",
        "docs": "/docs",
        "login_method": "application/x-www-form-urlencoded",
        "login_fields": ["username", "password"],
        "register_fields": [
        "first_name",
        "last_name",
        "student_number",
        "national_code",
        "phone_number",
        "gender",
        "address"
        ],
        "login_identifier": "national_code",
        "login_password": "student_number"
    }


@router.get(
    "/db",
    summary="تست دیتابیس",
    description="تست اتصال و سلامت دیتابیس"
)
async def test_database(db: Session = DBDep()):  # ✅ اصلاح شده
    """
    تست اتصال به دیتابیس و شمارش رکوردها.
    """
    try:
        # شمارش رکوردها
        user_count = db.query(User).count()
        role_count = db.query(Role).count()
        profile_count = db.query(StudentProfile).count()

        # تست query ساده
        latest_user = db.query(User).order_by(User.created_at.desc()).first()

        return {
            "database": "connected ✅",
            "tables": {
                "users": user_count,
                "roles": role_count,
                "student_profiles": profile_count
            },
            "latest_user": {
                "id": latest_user.id if latest_user else None,
                "student_number": latest_user.student_number if latest_user else None,
                "created_at": latest_user.created_at.isoformat() if latest_user and latest_user.created_at else None
            },
            "timestamp": "now"  # می‌توانید datetime.now() استفاده کنید
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"خطا در اتصال به دیتابیس: {str(e)}"
        )


@router.get(
    "/me",
    response_model=UserOut,
    summary="تست کاربر جاری",
    description="تست endpoint محافظت شده با توکن"
)
async def test_me(current_user: User = CurrentUser()):  # ✅ اصلاح شده
    """
    تست دریافت اطلاعات کاربر جاری.

    نیاز به توکن JWT معتبر دارد.
    """
    return {
        "id": current_user.id,
        "student_number": current_user.student_number,
        "role": current_user.role.name if current_user.role else None,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "additional_info": "این یک endpoint تستی است"
    }


@router.get(
    "/admin",
    summary="تست دسترسی ادمین",
    description="تست endpoint فقط برای ادمین‌ها"
)
async def test_admin_only(admin_user: User = AdminDep()):  # ✅ اصلاح شده
    """
    فقط کاربران با نقش admin می‌توانند به این endpoint دسترسی داشته باشند.
    """
    return {
        "message": "شما ادمین هستید! 🔐",
        "user": {
            "id": admin_user.id,
            "student_number": admin_user.student_number,
            "role": admin_user.role.name if admin_user.role else None
        },
        "permissions": [
            "create_users",
            "delete_users",
            "manage_roles",
            "view_all_data"
        ]
    }


@router.get(
    "/users",
    summary="لیست کاربران (تست)",
    description="نمایش لیست کاربران (برای تست)"
)
async def list_users(
    db: Session = DBDep(),  # ✅ اصلاح شده
    current_user: User = CurrentUser(),  # ✅ اصلاح شده
    limit: int = 10,
    offset: int = 0
):
    """
    نمایش لیست کاربران (برای اهداف تست).

    پارامترها:
    - limit: تعداد رکوردها در هر صفحه
    - offset: تعداد رکوردهایی که باید رد شوند
    """
    # فقط ادمین‌ها یا کاربران خاص می‌توانند لیست کاربران را ببینند
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="شما دسترسی به لیست کاربران را ندارید"
        )

    users = db.query(User).offset(offset).limit(limit).all()

    user_list = []
    for user in users:
        user_data = {
            "id": user.id,
            "student_number": user.student_number,
            "role": user.role.name if user.role else None,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }

        # اضافه کردن اطلاعات پروفایل اگر وجود دارد
        if user.profile:
            user_data["profile"] = {
                "national_code": user.profile.national_code,
                "phone_number": user.profile.phone_number,
                "gender": user.profile.gender
            }

        user_list.append(user_data)

    total_users = db.query(User).count()

    return {
        "total": total_users,
        "limit": limit,
        "offset": offset,
        "users": user_list
    }


@router.get(
    "/roles",
    summary="لیست نقش‌ها (تست)",
    description="نمایش لیست نقش‌های سیستم"
)
async def list_roles(db: Session = DBDep()):  # ✅ اصلاح شده
    """
    نمایش لیست نقش‌های موجود در سیستم.
    """
    roles = db.query(Role).all()

    role_list = []
    for role in roles:
        user_count = db.query(User).filter(User.role_id == role.id).count()

        role_list.append({
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "user_count": user_count,
            "users_sample": [
                user.student_number
                for user in db.query(User)
                .filter(User.role_id == role.id)
                .limit(3)
                .all()
            ]
        })

    return {
        "total_roles": len(roles),
        "roles": role_list
    }


@router.get(
    "/profile/{user_id}",
    summary="پروفایل کاربر (تست)",
    description="دریافت پروفایل یک کاربر خاص"
)
async def get_user_profile(
    user_id: int,
    db: Session = DBDep(),  # ✅ اصلاح شده
    current_user: User = CurrentUser()  # ✅ اصلاح شده
):
    """
    دریافت پروفایل کاربر.

    کاربران فقط می‌توانند پروفایل خودشان را ببینند
    مگر اینکه ادمین باشند.
    """
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="شما فقط می‌توانید پروفایل خودتان را ببینید"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="کاربر پیدا نشد"
        )

    profile_data = {
        "user": {
            "id": user.id,
            "student_number": user.student_number,
            "role": user.role.name if user.role else None,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    }

    if user.profile:
        profile_data["profile"] = {
            "national_code": user.profile.national_code,
            "phone_number": user.profile.phone_number,
            "gender": user.profile.gender,
            "address": user.profile.address,
            "created_at": user.profile.created_at.isoformat() if user.profile.created_at else None
        }

    return profile_data


@router.post(
    "/create-test-user",
    summary="ایجاد کاربر تستی",
    description="ایجاد یک کاربر تستی برای آزمایش"
)
async def create_test_user(
    db: Session = DBDep(),  # ✅ اصلاح شده
    current_user: User = AdminDep(),  # ✅ اصلاح شده
    student_number: str = "test12345",
    role_name: str = "user"
):
    """
    ایجاد یک کاربر تستی.

    فقط برای اهداف توسعه و تست.
    """
    from app.core.security import hash_password

    # بررسی وجود نقش
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"نقش '{role_name}' وجود ندارد"
        )

    # بررسی وجود کاربر با این شماره دانشجویی
    existing_user = db.query(User).filter(User.student_number == student_number).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="کاربر با این شماره دانشجویی از قبل وجود دارد"
        )

    # ایجاد کاربر
    user = User(
        student_number=student_number,
        hashed_password=hash_password(student_number),  # رمز = شماره دانشجویی
        role_id=role.id
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "کاربر تستی ایجاد شد",
        "user": {
            "id": user.id,
            "student_number": user.student_number,
            "role": role.name,
            "password": student_number,  # فقط برای نمایش در تست
            "note": "رمز عبور برابر با شماره دانشجویی است"
        }
    }


@router.get(
    "/health",
    summary="سلامت سیستم",
    description="چک سلامت کامل سیستم"
)
async def health_check(db: Session = DBDep()):  # ✅ اصلاح شده
    """
    بررسی سلامت کامل سیستم.

    موارد بررسی:
    1. اتصال به دیتابیس
    2. وجود جداول ضروری
    3. وجود نقش‌های پایه
    """
    health_status = {
        "status": "healthy",
        "timestamp": "now",  # datetime.now().isoformat()
        "checks": []
    }

    try:
        # ۱. چک دیتابیس
        db.execute("SELECT 1")
        health_status["checks"].append({
            "name": "database",
            "status": "healthy",
            "message": "اتصال به دیتابیس موفق"
        })
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"].append({
            "name": "database",
            "status": "unhealthy",
            "message": f"خطا در اتصال به دیتابیس: {str(e)}"
        })

    # ۲. چک جداول
    tables = ["users", "roles", "student_profiles"]
    for table in tables:
        try:
            db.execute(f"SELECT 1 FROM {table} LIMIT 1")
            health_status["checks"].append({
                "name": f"table_{table}",
                "status": "healthy",
                "message": f"جدول {table} وجود دارد"
            })
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"].append({
                "name": f"table_{table}",
                "status": "unhealthy",
                "message": f"جدول {table} وجود ندارد یا مشکل دارد"
            })

    # ۳. چک نقش‌های ضروری
    essential_roles = ["user", "admin"]
    for role_name in essential_roles:
        role = db.query(Role).filter(Role.name == role_name).first()
        if role:
            health_status["checks"].append({
                "name": f"role_{role_name}",
                "status": "healthy",
                "message": f"نقش {role_name} وجود دارد"
            })
        else:
            health_status["status"] = "warning"
            health_status["checks"].append({
                "name": f"role_{role_name}",
                "status": "warning",
                "message": f"نقش {role_name} وجود ندارد"
            })

    return health_status