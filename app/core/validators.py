import re
import unicodedata
from typing import Any, Optional


_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_DIGIT_TRANSLATION = str.maketrans(
    {**{ord(d): str(i) for i, d in enumerate(_PERSIAN_DIGITS)},
     **{ord(d): str(i) for i, d in enumerate(_ARABIC_DIGITS)}}
)


def _coerce_to_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)

def _normalize_and_require_pattern(
    value: Optional[str],
    pattern: str,
    error_message: str,
) -> Optional[str]:
    if value is None:
        return value
    normalized_value = normalize_digits(value)
    if not re.fullmatch(pattern, normalized_value):
        raise ValueError(error_message)
    return normalized_value

def normalize_digits(value: Any) -> Optional[str]:
        """
        نرمال‌سازی ورودی‌های عددی.

        - تبدیل ارقام فارسی/عربی به انگلیسی
        - حذف فاصله‌ها و کاراکترهای قالب‌بندی متداول
        - پشتیبانی از ورودی‌های غیررشته‌ای (مثل int)
        """
        text_value = _coerce_to_text(value)
        if text_value is None:
            return None

        normalized = unicodedata.normalize("NFKC", text_value).translate(_DIGIT_TRANSLATION).strip()
        # حذف انواع فاصله‌ها و علائم قالب‌بندی رایج
        normalized = re.sub(r"[\s\u200c\u200f\-_()]+", "", normalized)
        return normalized

def _normalize_fixed_digits(
    value: Any,
    *,
    length: int,
    field_name: str,
    invalid_message: Optional[str] = None,
) -> str:
    text_value = _coerce_to_text(value)
    normalized = normalize_digits(text_value) if text_value is not None else None
    if normalized is None or normalized == "":
        raise ValueError(f"{field_name} الزامی است")
    if re.fullmatch(r"\d+", normalized) and len(normalized) != length:
        raise ValueError(f"{field_name} باید {length} رقم باشد")



    if not re.fullmatch(rf"\d{{{length}}}", normalized):
        if invalid_message:
            raise ValueError(invalid_message)
        persian_length = str(length).translate(str.maketrans("0123456789", _PERSIAN_DIGITS))
        raise ValueError(f"{field_name} باید {persian_length} رقم باشد")

    return normalized

def validate_student_number(value: Any) -> Optional[str]:
    if value is None:
        return value
    return _normalize_fixed_digits(value, length=9, field_name="شماره دانشجویی")

def validate_phone_number(value: Any) -> Optional[str]:
    if value is None:
        return value

    text_value = _coerce_to_text(value)
    value = unicodedata.normalize("NFKC", text_value).translate(_DIGIT_TRANSLATION) if text_value is not None else None

    if not re.fullmatch(r"\d{11}", value):
        raise ValueError("شماره تماس باید ۱۱ رقم باشد")
    return value


def validate_national_code(value: Any) -> Optional[str]:
    if value is None:
        return value
    return _normalize_fixed_digits(
        value,
        length=10,
        field_name="کد ملی",
        invalid_message="کد ملی معتبر نیست",
    )

def validate_gender(value: Optional[str]) -> Optional[str]:
    if value is None:
        return value
    normalized_value = value.strip().lower()
    allowed_values = {
        "خواهر": "sister",
        "sister": "sister",
        "برادر": "brother",
        "brother": "brother",
    }
    normalized_gender = allowed_values.get(normalized_value)
    if not normalized_gender:
        raise ValueError("gender must be 'sister' or 'brother'")
    return normalized_gender