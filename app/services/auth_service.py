# app/services/auth_service.py
import logging

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import timedelta
from app.models.user import User
from app.models.role import Role
from app.models.student_profile import StudentProfile
from app.schemas.auth import RegisterRequest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    MAX_BCRYPT_PASSWORD_BYTES,
)
from app.core.validators import normalize_digits

def register_user(db: Session, data: RegisterRequest):
    """
    ثبت کاربر جدید در سیستم.

    Args:
        db: Session دیتابیس
        data: اطلاعات ثبت نام (RegisterRequest)
    """

    student_number = normalize_digits(data.student_number)
    national_code = normalize_digits(data.national_code)
    phone_number = normalize_digits(data.phone_number)

    if len(student_number.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="شماره دانشجویی نباید بیشتر از ۷۲ بایت باشد."
        )


    existing_user = db.query(User).filter(
        User.student_number == student_number).first()

    existing_profile = db.query(StudentProfile).filter(
        (StudentProfile.national_code == national_code)
        | (StudentProfile.student_number == student_number)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="شماره دانشجویی قبلاً ثبت شده است"
        )
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="کد ملی یا شماره دانشجویی قبلاً ثبت شده است"
        )

    try:
        # پیدا کردن نقش کاربر عادی
        role = db.query(Role).filter(Role.name == "user").first()

        if not role:
            # اگر نقش user وجود ندارد، آن را ایجاد کنید
            role = Role(name="user", description="کاربر عادی")
            db.add(role)
            db.flush()


        hashed_password = hash_password(student_number)


        # ایجاد کاربر
        user = User(
            student_number=student_number,
            hashed_password=hashed_password,
            role_id=role.id
        )

        db.add(user)
        db.flush()

            # ایجاد پروفایل دانشجویی
        profile = StudentProfile(
            user_id=user.id,
            first_name=data.first_name,
            last_name=data.last_name,
            national_code=national_code,
            student_number=student_number,
            phone_number=phone_number,
            gender=data.gender.value if hasattr(data.gender, "value") else data.gender,
            address=data.address
        )


        db.add(profile)
        db.commit()
        db.refresh(user)

    except IntegrityError as exc:
        db.rollback()
        logging.exception("Integrity error while registering user.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="اطلاعات وارد شده تکراری یا نامعتبر است."
        ) from exc

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc)
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()
        logging.exception("Database error while registering user.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ثبت‌نام با خطا مواجه شد. لطفاً دوباره تلاش کنید."
        ) from exc

    return user



def authenticate_user(db: Session, national_code: str, password: str):

    user = (
        db.query(User)
        .join(StudentProfile, StudentProfile.user_id == User.id)
        .filter(StudentProfile.national_code == national_code)
        .first()
    )

    # بررسی وجود کاربر و صحت رمز عبور (که در اینجا باید برابر با شماره دانشجویی باشد)
    if not user or not verify_password(password, user.hashed_password):
        return None

    return user


def enforce_single_national_id_authentication(db: Session, user: User) -> None:
    """
    جلوگیری از احراز هویت تکراری با کد ملی.

    اگر کاربر قبلاً با کد ملی خود احراز هویت کرده باشد،
    خطا برگردانده می‌شود. در غیر این صورت، وضعیت احراز هویت ثبت می‌شود.
    """
    profile = db.query(StudentProfile).filter(
        StudentProfile.user_id == user.id
    ).first()

    if not profile:
        return

    if profile.has_authenticated:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="این کد ملی قبلاً برای احراز هویت استفاده شده است"
        )

    profile.has_authenticated = True
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logging.exception("Database error while updating authentication status.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="خطا در ثبت وضعیت احراز هویت. لطفاً دوباره تلاش کنید."
        ) from exc


def create_token_for_user(user: User):
    """ ایجاد توکن JWT برای کاربر. Args: user: شیء کاربر Returns: dict: توکن دسترسی """
    national_code = user.profile.national_code if getattr(user, "profile", None) else None
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.student_number,
            "user_id": user.id,
            "national_code": national_code,
            "role": user.role.name if user.role else "user",
        },
        expires_delta=access_token_expires,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }
