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
    ACCESS_TOKEN_EXPIRE_MINUTES
)


def register_user(db: Session, data: RegisterRequest):
    """
    ثبت کاربر جدید در سیستم.

    Args:
        db: Session دیتابیس
        data: اطلاعات ثبت نام (RegisterRequest)
    """


    existing_user = db.query(User).filter(
        User.student_number == data.student_number
    ).first()

    existing_profile = db.query(StudentProfile).filter(
        StudentProfile.national_code == data.national_code
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="شماره دانشجویی قبلاً ثبت شده است"
        )
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="کد ملی قبلاً ثبت شده است"
        )

    try:
        # پیدا کردن نقش کاربر عادی
        role = db.query(Role).filter(Role.name == "user").first()

        if not role:
            # اگر نقش user وجود ندارد، آن را ایجاد کنید
            role = Role(name="user", description="کاربر عادی")
            db.add(role)
            db.flush()
            # رمز عبور برابر با شماره دانشجویی
        hashed_password = hash_password(data.student_number[:72])

    # ایجاد کاربر
        user = User(
            student_number=data.student_number,
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
            national_code=data.national_code,
            student_number=data.student_number,
            phone_number=data.phone_number,
            gender=data.gender.value if hasattr(data.gender, 'value') else data.gender,
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

    return user



def authenticate_user(db: Session, national_code: str, password: str):
    """
    احراز هویت کاربر با شماره دانشجویی و رمز عبور.

    Args:
        db: Session دیتابیس
        student_number: شماره دانشجویی
        password: رمز عبور

    Returns:
        User or None: کاربر پیدا شده یا None
    """
    # پیدا کردن کاربر از طریق کد ملی پروفایل
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
    db.commit()


def create_token_for_user(user: User):
    """ ایجاد توکن JWT برای کاربر. Args: user: شیء کاربر Returns: dict: توکن دسترسی """
    national_code = user.profile.national_code if getattr(user, "profile", None) else None
    access_token_expires =\
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token( data={
        "sub": user.student_number,
        "user_id": user.id,
        "national_code": national_code,
        "role": user.role.name if user.role else
        "user" },
                                        expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }
