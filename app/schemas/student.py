from pydantic import BaseModel, Field, field_validator
from typing import Optional
from enum import Enum

# Enum برای جنسیت
class GenderEnum(str, Enum):
    sister = "sister"
    brother = "brother"

# Enum برای وضعیت حساب
class AccountStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"


# مدل پایه برای پروفایل دانشجو
class StudentProfileBase(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    national_code: str = Field(..., pattern=r"^\d{10}$")
    student_number: str = Field(..., pattern=r"^\d{9}$")
    phone_number: str = Field(..., pattern=r"^\d{11}$")
    gender: GenderEnum
    address: Optional[str] = Field(None, max_length=100)

    model_config = {
        "from_attributes": True
    }


# کلاس برای بروزرسانی پروفایل توسط دانشجو
class StudentProfileUpdate(BaseModel):
    national_code: Optional[str] = Field(None, pattern=r"^\d{10}$")
    phone_number: Optional[str] = Field(None, pattern=r"^\d{11}$")
    gender: Optional[str] = None
    address: Optional[str] = Field(None, max_length=100)

    @field_validator("gender")
    def validate_gender(cls, v):
        if v in ["خواهر", "sister"]:
            return "sister"
        elif v in ["برادر", "brother"]:
            return "brother"
        elif v is not None:
            raise ValueError("gender must be 'sister' or 'brother'")
        return v

    model_config = {
        "from_attributes": True
    }


# کلاس برای بروزرسانی پروفایل توسط ادمین
class AdminStudentUpdate(StudentProfileBase):
    status: AccountStatus


# کلاس خروجی پروفایل دانشجویی (Student)
class StudentProfileOut(StudentProfileBase):
    id: int
    status: AccountStatus

    model_config = {
        "from_attributes": True
    }


# مدل خروجی ساده برای ORM / دیتابیس
class StudentProfileOutDB(BaseModel):
    id: int
    student_number: str
    national_code: str
    phone_number: str
    gender: GenderEnum
    address: Optional[str]

    model_config = {
        "from_attributes": True
    }
