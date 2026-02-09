from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.student_profile import StudentProfile
from app.models.user import User
from app.schemas.student import StudentProfileUpdate, AdminStudentUpdate


def _check_uniqueness(
    db: Session,
    national_code: str,
    student_number: str,
    exclude_user_id: int,
):
    """
    بررسی یکتایی کد ملی و شماره دانشجویی برای جلوگیری از تکرار.
    """
    conflict = (
        db.query(StudentProfile)
        .filter(
            StudentProfile.user_id != exclude_user_id,
            (StudentProfile.national_code == national_code)
            | (StudentProfile.student_number == student_number),
        )
        .first()
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="کد ملی یا شماره دانشجویی تکراری است",
        )


def get_my_profile(db: Session, user: User) -> StudentProfile:
    """
    دریافت پروفایل کاربر فعلی.
    """
    profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == user.id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="پروفایل یافت نشد")
    return profile


def update_my_profile(
    db: Session,
    user: User,
    data: StudentProfileUpdate,
) -> StudentProfile:
    """
    به‌روزرسانی پروفایل توسط خود کاربر.
    """
    profile = get_my_profile(db, user)

    # بررسی یکتایی شماره دانشجویی و کد ملی
    national_code = data.national_code if data.national_code is not None else profile.national_code
    _check_uniqueness(
        db,
        national_code,
        profile.student_number,
        user.id,
    )

    # به‌روزرسانی اطلاعات پروفایل
    for field, value in data.model_dump().items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile


# ---------------- ADMIN ----------------

def get_all_students(db: Session):
    """
    دریافت تمام پروفایل‌های دانشجویی برای ادمین.
    """
    return db.query(StudentProfile).all()


def get_student_by_id(db: Session, student_id: int) -> StudentProfile:
    """
    دریافت پروفایل یک دانشجو با شناسه یکتا.
    """
    profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.id == student_id)
        .first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="دانشجو یافت نشد")
    return profile


def admin_update_student(
    db: Session,
    student_id: int,
    data: AdminStudentUpdate,
) -> StudentProfile:
    """
    به‌روزرسانی پروفایل دانشجویی توسط ادمین.
    """
    profile = get_student_by_id(db, student_id)

    # بررسی یکتایی شماره دانشجویی و کد ملی
    _check_uniqueness(
        db,
        data.national_code,
        data.student_number,
        profile.user_id,
    )

    # به‌روزرسانی اطلاعات پروفایل توسط ادمین
    for field, value in data.model_dump().items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile



