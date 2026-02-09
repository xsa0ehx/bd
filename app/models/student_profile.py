from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from fastapi import HTTPException
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # اطلاعات شخصی
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    national_code = Column(String(10), unique=True, nullable=False, index=True)
    student_number = Column(String(20), unique=True, nullable=False, index=True)
    phone_number = Column(String(11), nullable=False)
    gender = Column(String(10), nullable=False)  # brother/sister
    address = Column(String(200))
    additional_info = Column(Text, nullable=True)  # اطلاعات اضافی
    has_authenticated = Column(Boolean, default=False, nullable=False)

    # timestamp‌ها
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # رابطه
    user = relationship("User", back_populates="profile")

    def __repr__(self):
        return f"<StudentProfile(id={self.id}, user_id={self.user_id}, national_code='{self.national_code}')>"

    def to_dict(self):
        """تبدیل شیء پروفایل به دیکشنری."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "national_code": self.national_code,
            "student_number": self.student_number,
            "phone_number": self.phone_number,
            "gender": self.gender,
            "address": self.address,
            "additional_info": self.additional_info,
            "has_authenticated": self.has_authenticated,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @property
    def is_brother(self):
        """بررسی اینکه جنسیت brother است یا نه."""
        return self.gender.lower() == "brother"

    @property
    def is_sister(self):
        """بررسی اینکه جنسیت sister است یا نه."""
        return self.gender.lower() == "sister"

    @staticmethod
    def check_unique(db, national_code: str, student_number: str, exclude_user_id: int = None):
        """
        بررسی تکراری بودن شماره دانشجویی یا کد ملی
        """
        conflict_query = db.query(StudentProfile).filter(
            (StudentProfile.national_code == national_code)
            | (StudentProfile.student_number == student_number)
        )

        if exclude_user_id is not None:
            conflict_query = conflict_query.filter(StudentProfile.user_id != exclude_user_id)

        conflict = conflict_query.first()

        if conflict:
            raise HTTPException(
                status_code=400,
                detail="کد ملی یا شماره دانشجویی تکراری است"
            )
