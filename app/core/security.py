import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.deps import DBDep
from app.models.user import User
from app.core.confing import settings

# تنظیمات
SECRET_KEY = settings.secret_key  # در production تغییر دهید
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
MAX_BCRYPT_PASSWORD_BYTES = 72
# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


if SECRET_KEY == "CHANGE_THIS_SECRET_KEY":
    logging.getLogger(__name__).warning(
        "SECRET_KEY is using the default value; set SECRET_KEY in production."
    )

# Exception
credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="توکن نامعتبر یا منقضی شده است",
    headers={"WWW-Authenticate": "Bearer"},
)


def hash_password(password: str) -> str:
    """هش کردن رمز عبور."""
    safe_password = normalize_password(password)
    return bcrypt.hashpw(safe_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """تأیید رمز عبور."""
    try:
        safe_password = normalize_password(plain_password)
    except ValueError:
        return False

    try:
        return bcrypt.checkpw(
            safe_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        logging.getLogger(__name__).warning("Invalid password hash encountered.")
        return False

def normalize_password(password: str) -> str:

    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_BCRYPT_PASSWORD_BYTES:
        raise ValueError("رمز عبور نباید بیشتر از ۷۲ بایت باشد.")

    return password


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """ساخت توکن JWT."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = DBDep()

) -> User:
    """
    اعتبارسنجی توکن JWT و برگرداندن کاربر.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        student_number: str = payload.get("sub")
        national_code: str = payload.get("national_code")  # اضافه کردن کد ملی به payload

        if student_number is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.student_number == student_number).first()

    if user is None:
        raise credentials_exception

    return user


def get_current_admin(
        current_user: User = Depends(get_current_user),
):
    """
    Dependency برای اطمینان از admin بودن کاربر
    """
    if  not current_user.role or current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="شما دسترسی لازم را ندارید"
        )
    return current_user
