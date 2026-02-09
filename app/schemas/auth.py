from typing import Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum

# Enum برای جنسیت
class GenderEnum(str, Enum):
    sister = "sister"
    brother = "brother"

# Schema برای درخواست ثبت نام
class RegisterRequest(BaseModel):
    first_name: str = Field(..., description="نام", min_length=2, max_length=50)
    last_name: str = Field(..., description="نام خانوادگی", min_length=2, max_length=50)
    student_number: str = Field(..., description="شماره دانشجویی ۹ رقمی")
    national_code: str = Field(..., description="کد ملی ۱۰ رقمی")
    phone_number: str = Field(..., description="شماره تماس ۱۱ رقمی")
    gender: GenderEnum
    address: Optional[str] = None

    @field_validator("student_number")
    def validate_student_number(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 9:
            raise ValueError("شماره دانشجویی باید ۹ رقم باشد")
        return value

    @field_validator("national_code")
    def validate_national_code(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 10:
            raise ValueError("کد ملی باید ۱۰ رقم باشد")
        return value

    @field_validator("phone_number")
    def validate_phone_number(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 11:
            raise ValueError("شماره تماس باید ۱۱ رقم باشد")
        return value

    class Config:
        json_schema_extra = {
            "example": {
                "first_name": "زهرا",
                "last_name": "محمدی",
                "student_number": "123456789",
                "national_code": "0123456789",
                "phone_number": "09123456789",
                "gender": "sister",
                "address": "تهران، خیابان انقلاب"
            }
        }


# Schema برای درخواست ورود
class LoginRequest(BaseModel):
    national_code: str = Field(..., description="کد ملی ۱۰ رقمی")
    student_number: str = Field(..., description="شماره دانشجویی ۹ رقمی")

    @field_validator("national_code")
    def validate_login_national_code(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 10:
            raise ValueError("کد ملی باید ۱۰ رقم باشد")
        return value

    @field_validator("student_number")
    def validate_login_student_number(cls, value: str) -> str:
        if not value.isdigit() or len(value) != 9:
            raise ValueError("شماره دانشجویی باید ۹ رقم باشد")
        return value

    class Config:
        json_schema_extra = {
            "example": {
                "national_code": "3200261196",
                "student_number": "404370044"
            }
        }

# Schema برای پاسخ توکن
class Token(BaseModel):
    access_token: str = Field(..., description="توکن دسترسی JWT")
    token_type: str = Field(default="bearer", description="نوع توکن")
    expires_in: Optional[int] = Field(default=3600, description="زمان انقضا به ثانیه")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }

# Schema برای پاسخ ثبت نام
class RegisterResponse(BaseModel):
    message: str = Field(..., description="پیام پاسخ")
    user_id: int = Field(..., description="شناسه کاربر ایجاد شده")
    student_number: str = Field(..., description="شماره دانشجویی")
    role: str = Field(..., description="نقش کاربر")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "ثبت‌نام با موفقیت انجام شد",
                "user_id": 1,
                "student_number": "123456789",
                "role": "user"
            }
        }

