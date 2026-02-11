import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Tuple


def _parse_bool(value: str, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(value: str, default: Tuple[str, ...]) -> Tuple[str, ...]:
    if value is None:
        return default
    items = [item.strip() for item in value.split(",") if item.strip()]
    return tuple(items) if items else default


@dataclass(frozen=True)

class Settings:
    database_url: str
    sql_echo: bool
    cors_allow_origins: Tuple[str, ...]
    cors_allow_credentials: bool
    cors_allow_methods: Tuple[str, ...]
    cors_allow_headers: Tuple[str, ...]
    secret_key: str
    access_token_expire_minutes: int
    cookie_secure: bool
    log_level: str
    admin_interface_password: str
    admin_lockout_minutes: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./basij.db"),
        sql_echo=_parse_bool(os.getenv("SQL_ECHO"), False),
        cors_allow_origins=_parse_csv(os.getenv("CORS_ALLOW_ORIGINS"), ("*",)),
        cors_allow_credentials=_parse_bool(os.getenv("CORS_ALLOW_CREDENTIALS"), True),
        cors_allow_methods=_parse_csv(os.getenv("CORS_ALLOW_METHODS"), ("*",)),
        cors_allow_headers=_parse_csv(os.getenv("CORS_ALLOW_HEADERS"), ("*",)),
        secret_key=os.getenv("SECRET_KEY", "CHANGE_THIS_SECRET_KEY"),
        access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
        cookie_secure=_parse_bool(os.getenv("COOKIE_SECURE"), False),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        admin_interface_password=os.getenv(
            "ADMIN_INTERFACE_PASSWORD",
            '{aZ9$kL2#mN8&qR5*vX1@pY4%wB".}',
        ),
        admin_lockout_minutes=int(os.getenv("ADMIN_LOCKOUT_MINUTES", "15")),
    )


settings = get_settings()